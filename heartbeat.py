import time
import os
import threading
import requests
import pyautogui
import traceback
import json
import subprocess
import random
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE") # Reserved for future use

WATCH_PATH = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK"
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git"]
IGNORE_FILES = [
    "heartbeat.log", "heartbeat.lock", "heartbeat.py", "test_sync.py", "temp.jpg",
    ".tmp", ".m4v", ".aac", ".prsl", "._00_", "placeholder", "clip_"
]
COOLDOWN_SECONDS = 5  # Reduced cooldown
DEBOUNCE_SECONDS = 8.0 # Seconds to wait for file system silence

# Global cache to persist across observer restarts
last_sent_cache = {}
last_size_cache = {}
pending_timers = {}

# --- SINGLETON LOCK ---
import msvcrt
LOCK_FILE = "heartbeat.lock"
lock_file_handle = None

def get_lock():
    global lock_file_handle
    try:
        lock_file_handle = open(LOCK_FILE, "w")
        msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        return True
    except:
        return False

if not get_lock():
    print("Another instance of heartbeat.py is already running. Exiting.")
    exit(0)

if not URL or not KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    exit(1)

supabase = create_client(URL, KEY)

# Mapping file types to actions and moods
WORKFLOW_MAP = {
    ".prproj": {"label": "Deep in the Edit", "mood": "focused"},
    ".aep":    {"label": "Motion Graphics & FX", "mood": "creative"},
    ".psd":    {"label": "Graphic Design", "mood": "artistic"},
    ".flp":    {"label": "Audio Mastering", "mood": "musical"}, 
    ".mp4":    {"label": "Exporting Final Render", "mood": "success"}
}

def get_project_name(file_path):
    """Extract project name from path (e.g., .../DFP/Dr Drive Podcast/ -> Dr Drive)."""
    parts = file_path.split(os.sep)
    try:
        # Detect DFP structure
        if "DFP" in parts:
            idx = parts.index("DFP")
            if idx + 1 < len(parts):
                name = parts[idx+1]
                # Clean up "Dr Drive Podcast" to "Dr Drive"
                return name.replace(" Podcast", "").replace(" Project", "").strip()
        
        # Fallback to relpath
        relative = os.path.relpath(file_path, WATCH_PATH)
        parts = relative.split(os.sep)
        if len(parts) > 1:
            return parts[0]
        return "General Workspace"
    except:
        return "Studio Project"

def broadcast_to_buffer(message, profile_id=None, asset_url=None, is_video=False):
    if not BUFFER_TOKEN or not profile_id or "your_buffer" in BUFFER_TOKEN:
        log_msg("Buffer credentials or Profile ID missing. Skipping broadcast.")
        return

    url = "https://api.buffer.com"
    
    # GraphQL mutation for creating a post with assets (Story or Reel)
    mutation = """
    mutation CreateNewPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    
    # Select asset type
    assets = {}
    if asset_url:
        if is_video:
            assets = {"videos": [{"url": asset_url}]}
        else:
            assets = {"images": [{"url": asset_url}]}

    variables = {
        "input": {
            "text": message,
            "channelId": profile_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": assets,
            "metadata": {
                "instagram": {
                    "type": "reels" if is_video else "story",
                    "shouldShareToFeed": False
                }
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BUFFER_TOKEN}"
    }
    
    try:
        response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                log_msg(f"Buffer GraphQL Error: {data['errors']}")
            else:
                try:
                    post_id = data['data']['createPost']['post']['id']
                    log_msg(f"🚀 Buffer Success! Post created with ID: {post_id} on channel {profile_id}")
                except:
                    log_msg(f"Buffer Response Data: {data}")
        else:
            log_msg(f"Buffer HTTP error: {response.status_code} - {response.text}")
    except Exception as e:
        log_msg(f"Buffer broadcast script error: {e}")

# --- SUPABASE HARDENING ---
def get_supabase_client():
    try:
        return create_client(URL, KEY)
    except Exception as e:
        print(f"Supabase Client Init Error: {e}")
        return None

supabase = get_supabase_client()

def log_msg(msg):
    """Robust logging that works even in background mode and handles emojis."""
    full_msg = f"[{time.ctime()}] {msg}"
    # Safe print for Windows console
    try:
        print(full_msg.encode('ascii', 'ignore').decode('ascii'))
    except:
        pass
        
    try:
        with open("heartbeat.log", "a", encoding='utf-8') as f:
            f.write(full_msg + "\n")
    except: pass

class HeartbeatHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        # IRON SEAL: Immediate suppression of internal system noise
        if any(f in path for f in IGNORE_FILES + [".git"]):
            return
        
        log_msg(f"[WATCHER] Change: {os.path.basename(event.src_path)}")
        self.process_event(event)
        
    def on_created(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        if any(f in path for f in ["heartbeat.log", "heartbeat.py", "heartbeat.lock", "test_sync.py", "temp.jpg", ".git"]):
            return
        
        log_msg(f"[WATCHER] Created: {os.path.basename(event.src_path)}")
        self.process_event(event)

    def process_event(self, event):
        file_path = event.src_path
        ext = os.path.splitext(file_path)[1].lower().strip()
            
        # DEEP DEBUG
        log_msg(f"[DEBUG] Ext Seen: '{ext}' | Length: {len(ext)}")

        # FLEXIBLE MATCHING
        workflow = None
        for key in WORKFLOW_MAP:
            if ext.startswith(key):
                workflow = WORKFLOW_MAP[key]
                break

        if workflow:
            project_name = get_project_name(file_path)
            
            # --- OPEN VS SAVE FILTER ---
            try:
                current_size = os.path.getsize(file_path)
                last_size = last_size_cache.get(file_path)
                
                # If it's a project file (not a render) and size hasn't changed, ignore it.
                # This prevents "Open" events from triggering pulses.
                if ext != ".mp4" and last_size is not None and current_size == last_size:
                    # log_msg(f"[WATCHER] Size unchanged for {os.path.basename(file_path)}. Skipping pulse.")
                    return
                
                last_size_cache[file_path] = current_size
            except Exception as e:
                # If we can't get the size (e.g. file locked/temp), proceed anyway
                pass

            log_msg(f"[WATCHER] Mapping: {project_name} | {workflow['label']}")
            
            # --- DEBOUNCE LOGIC ---
            # Group events by project and label
            debounce_key = f"{project_name}_{workflow['label']}"
            
            if debounce_key in pending_timers:
                pending_timers[debounce_key].cancel()
                
            # Schedule the actual broadcast
            timer = threading.Timer(
                DEBOUNCE_SECONDS, 
                self.dispatch_heartbeat, 
                args=[project_name, workflow, file_path]
            )
            pending_timers[debounce_key] = timer
            timer.start()

    def dispatch_heartbeat(self, project_name, workflow, file_path):
        """The actual logic that sends data to Supabase, after debouncing."""
        try:
            # COOLDOWN (Burst Mode: 15s)
            cooldown_key = f"{project_name}_{workflow['label']}"
            current_time = time.time()
            if cooldown_key in last_sent_cache:
                if current_time - last_sent_cache[cooldown_key] < 15:
                    return
            
            last_sent_cache[cooldown_key] = current_time
            
            # 1. PREPARE METADATA
            ext = os.path.splitext(file_path)[1].lower().strip()
            mood = workflow['mood']
            quote = get_random_quote()

            software_map = {
                ".prproj": "Premiere Pro", ".psd": "Photoshop", ".aep": "After Effects",
                ".wav": "Ableton Live", ".mp4": "Media Encoder", ".mov": "DaVinci Resolve",
                ".png": "Graphic Engine", ".jpg": "Graphic Engine"
            }
            software = software_map.get(ext, "Creative Engine")

            # 2. CAPTURE VISION / VIDEO (Synchronous)
            asset_url = ""
            is_video = (ext == ".mp4")
            
            # For MP4s, we extract a random 10s highlight clip instead of the whole file
            asset_file = None
            if is_video:
                log_msg(f">>> [VIDEO] Extracting highlight from {os.path.basename(file_path)}...")
                asset_file = extract_random_clip(file_path)
            
            if not asset_file:
                asset_file = capture_screenshot()
            
            if asset_file:
                try:
                    with open(asset_file, 'rb') as f:
                        file_ext = os.path.splitext(asset_file)[1]
                        storage_path = f"pulses/{int(time.time())}{file_ext}"
                        supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                        asset_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                    # Cleanup screenshot/clip but keep project video
                    if ("screenshot_" in asset_file or "clip_" in asset_file) and os.path.exists(asset_file):
                        os.remove(asset_file)
                except Exception as e:
                    log_msg(f"[IMAGING/VIDEO ERROR] {e}")

            # 3. DISPATCH FULL PULSE TO SUPABASE
            data = {
                "project_name": project_name,
                "action_label": workflow["label"],
                "mood_tag": f"{mood}|Neural link active.|{asset_url}|{software}|{quote}", 
                "source": "Windows-Workstation",
                "is_milestone": is_video
            }
            
            log_msg(f">>> [SYNC] Dispatching pulse for {project_name} via {software}...")
            res = supabase.table("studio_heartbeat").insert(data).execute()
            
            if res.data:
                log_msg(f">>> [SYNC] SUCCESS! Vision Linked. Pulse ID: {res.data[0]['id']}")
            else:
                log_msg(">>> [SYNC ERROR] Insert failed.")

            # 4. ROUTE TO BUFFER
            if data["is_milestone"]:
                # Determine Target Channel
                buffer_profile = BUFFER_PROFILE_ID_MAIN
                proj_upper = project_name.upper()
                
                if "LANNA" in proj_upper:
                    buffer_profile = BUFFER_PROFILE_ID_LANNA
                elif any(x in proj_upper for x in ["BLUE", "MUSIC", "CHROMATIC", "TRIANGLE"]):
                    buffer_profile = BUFFER_PROFILE_ID_BLUE
                
                msg = f"🚀 Project Update: #{project_name} | {workflow['label']} complete. View live: feed.in-no-v8.com"
                if is_video:
                    msg = f"🔥 New Clip: #{project_name} in progress. #{software} workflow. Live feed: feed.in-no-v8.com"
                
                broadcast_to_buffer(msg, profile_id=buffer_profile, asset_url=asset_url, is_video=is_video)
                
        except Exception as e:
            err_msg = traceback.format_exc()
            log_msg(f">>> [SYNC ERROR] {e}\n{err_msg}")

    def upload_to_supabase_storage(self, file_path):
        """Upload a milestone image to Supabase Storage."""
        filename = os.path.basename(file_path)
        storage_path = f"{int(time.time())}_{filename}"
        
        try:
            with open(file_path, "rb") as f:
                supabase.storage.from_("studio-assets").upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": f"image/{filename.split('.')[-1]}"}
                )
            print(f"Uploaded to Studio Assets: {storage_path}")
        except Exception as e:
            print(f"Storage upload error: {e}")

# --- HELPER FUNCTIONS ---
QUOTES = [
    "Plans are nothing; planning is everything. – Eisenhower",
    "Creativity is intelligence having fun. – Einstein",
    "Simplicity is the ultimate sophistication. – Da Vinci",
    "Design is how it works. – Steve Jobs",
    "The best way to predict the future is to create it. – Peter Drucker",
    "Make it simple, but significant. – Don Draper",
    "Creativity is a wild mind and a disciplined eye. – Dorothy Parker",
    "Everything you can imagine is real. – Pablo Picasso",
    "You can't use up creativity. The more you use, the more you have. – Maya Angelou",
    "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away. – Saint-Exupéry",
    "The secret to creativity is knowing how to hide your sources. – Einstein",
    "Art is the elimination of the unnecessary. – Picasso",
    "Don't wait for inspiration. It comes while working. – Henri Matisse",
    "The computer is the most remarkable tool that we've ever come up with. – Steve Jobs",
    "Creativity is piercing the mundane to find the marvelous. – Bill Moyers",
    "Great things are done by a series of small things brought together. – Van Gogh",
    "Art is not what you see, but what you make others see. – Edgar Degas",
    "Logic will get you from A to B. Imagination will take you everywhere. – Einstein",
    "There is no doubt that creativity is the most important human resource. – Edward de Bono",
    "Innovation distinguishes between a leader and a follower. – Steve Jobs",
    "The world is but a canvas to our imagination. – Henry David Thoreau",
    "Music is the shorthand of emotion. – Leo Tolstoy",
    "Where words fail, music speaks. – Hans Christian Andersen",
    "The details are not the details. They make the design. – Charles Eames",
    "An essential aspect of creativity is not being afraid to fail. – Edwin Land",
    "To live a creative life, we must lose our fear of being wrong. – Joseph Chilton Pearce",
    "Creativity involves breaking out of established patterns in order to look at things in a different way. – Edward de Bono"
]

def get_random_quote():
    return QUOTES[int(time.time()) % len(QUOTES)]

def extract_random_clip(video_path):
    """Extracts a random 10-second clip from an MP4 file using FFmpeg."""
    try:
        # 1. Get Duration using ffprobe
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
        duration = float(subprocess.check_output(cmd).decode().strip())
        
        if duration < 12:
            return video_path # Too short to clip properly, use original
            
        # 2. Pick random start (at least 10s before end)
        start = random.uniform(2, max(2, duration - 12))
        output_file = f"clip_{int(time.time())}.mp4"
        
        # 3. Extract 10s clip with vertical 1080x1920 center-crop
        # Using libx264 for compatibility
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', '10', '-i', video_path,
            '-vf', "scale=w=-1:h=1920,crop=1080:1920",
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', 
            '-c:a', 'aac', '-b:a', '128k', output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except Exception as e:
        log_msg(f"[CLIP ERROR] {e}")
        return None

def capture_screenshot():
    """Captures the current workstation screen as a 'Live Interface' snapshot."""
    try:
        screenshot = pyautogui.screenshot()
        # Downscale for performance
        screenshot = screenshot.resize((1280, 720))
        filename = f"screenshot_{int(time.time())}.jpg"
        screenshot.save(filename, "JPEG", quality=70)
        return filename
    except Exception as e:
        log_msg(f"Screenshot capture failed: {e}")
        return None

if __name__ == "__main__":
    # Startup Scan: Populate last_size_cache to avoid "Open" pulses on first launch
    log_msg("Initializing Studio Pulse Vision Pipeline...")
    for root, dirs, files in os.walk(WATCH_PATH):
        if any(ignore in root for ignore in IGNORE_FOLDERS): continue
        for f in files:
            ext = os.path.splitext(f)[1].lower().strip()
            if any(key in ext for key in WORKFLOW_MAP):
                path = os.path.join(root, f)
                try: last_size_cache[path] = os.path.getsize(path)
                except: pass
    log_msg(f"Primed {len(last_size_cache)} project files.")

    while True:
        try:
            event_handler = HeartbeatHandler()
            observer = Observer()
            observer.schedule(event_handler, WATCH_PATH, recursive=True)
            observer.start()
            print(f"Monitoring {WATCH_PATH} with Buffer integration and Echo Fix (Active)...")
            
            while observer.is_alive():
                time.sleep(1)
                
        except Exception as e:
            print(f"Watcher error: {e}. Restarting in 10 seconds...")
            try:
                observer.stop()
            except:
                pass
            time.sleep(10)
        except KeyboardInterrupt:
            observer.stop()
            break
            
    observer.join()
