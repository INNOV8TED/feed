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
from datetime import datetime
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

# DYNAMIC WATCH PATH: Monitor the parent of the current script location
WATCH_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git"]
IGNORE_FILES = [
    "heartbeat.log", "heartbeat.lock", "heartbeat.py", "test_sync.py", "temp.jpg",
    ".tmp", ".m4v", ".aac", ".prsl", "._00_", "placeholder", "clip_", "audio_pulse_"
]
COOLDOWN_SECONDS = 5  # Reduced cooldown
DEBOUNCE_SECONDS = 5.0 # Increased responsiveness
DAILY_BUFFER_LIMIT = 8  # Safe limit for Free Plan
QUOTA_FILE = "buffer_quota.json"

# Global cache to persist across observer restarts
last_sent_cache = {}
# Persistence Cache
CACHE_FILE = "studio_cache.json"
last_size_cache = {}

def load_cache():
    global last_size_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                last_size_cache = json.load(f)
            log_msg(f"◈ [CACHE] Loaded {len(last_size_cache)} project states.")
        except:
            last_size_cache = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(last_size_cache, f)
    except:
        pass

load_cache()

# ECHO-ZERO LOCK
last_broadcast_time = 0
BROADCAST_LOCK_PERIOD = 20  # Increased for stability
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

# Expanded Label Pool for Variety
LABEL_POOL = {
    "edit":     ["Deep in the Edit", "Cutting the Master", "Timeline Sculpting", "Visual Storytelling", "Assembly Phase", "Edit Lock In Progress", "Color Correction"],
    "motion":   ["Motion Graphics & FX", "Visual Synthesis", "Dynamic Simulation", "After Effects Magic", "Kinetic Design", "FX Pass", "Animating Reality"],
    "graphic":  ["Graphic Design", "Visual Prototyping", "Digital Alchemy", "Aesthetic Refinement", "Composition Phase", "Pixel Perfecting", "Texture Mapping", "Branding Forge"],
    "audio":    ["Audio Mastering", "Sonic Engineering", "Melodic Synthesis", "Frequency Sculpting", "Mixing Session", "Atmospheric Layering", "Rhythm Engine Active"],
    "render":   ["Exporting Master", "Finalizing Visuals", "Rendering Sequence", "Baking Pixels", "Outputting Production", "Encoding Final Cut"]
}

# Mapping file types to categories and moods
WORKFLOW_MAP = {
    ".prproj": {"category": "edit",    "mood": "focused"},
    ".aep":    {"category": "motion",  "mood": "creative"},
    ".psd":    {"category": "graphic", "mood": "artistic"},
    ".flp":    {"category": "audio",   "mood": "musical"}, 
    ".wav":    {"category": "audio",   "mood": "musical"},
    ".mp3":    {"category": "audio",   "mood": "musical"},
    ".jpg":    {"category": "graphic", "mood": "artistic"},
    ".png":    {"category": "graphic", "mood": "artistic"},
    ".mp4":    {"category": "render",  "mood": "accomplished"},
    ".mov":    {"category": "render",  "mood": "accomplished"}
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

def broadcast_to_buffer(text, profile_id, asset_url=None, is_video=False, post_type="REEL"):
    """Broadcasts a message to a specific Buffer profile using GraphQL."""
    # --- CURATED SCHEDULE: 1 REEL AND 1 GRID POST PER CHANNEL PER DAY ---
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        quota = {}
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, 'r') as f:
                quota = json.load(f)
        
        # Structure: quota[date][profile_id][post_type] = 1
        if today not in quota: quota[today] = {}
        if profile_id not in quota[today]: quota[today][profile_id] = {}
        
        # INCREASED QUOTA: 1 Reel, 1 Story, 1 Grid Post per channel per day
        if quota[today][profile_id].get(post_type, 0) >= 1:
            log_msg(f"◈ [QUOTA] Daily {post_type} for channel {profile_id[-4:]} is full.")
            return
            
        # Mark as sent
        quota[today][profile_id][post_type] = 1
        with open(QUOTA_FILE, 'w') as f:
            json.dump(quota, f)
    except Exception as e:
        log_msg(f"[QUOTA ERROR] {e}")

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

    # Selecy hashtags based on content
    tags = " #StudioPulse #Innov8Labs #CreativeProcess #NeuralLink"
    if is_video: tags += " #Reel #Production"
    else: tags += " #StudioVision #BehindTheScenes"

    # Neural Branding Description
    description = f"◈ STUDIO BROADCAST ◈\n\n{text}\n\n📍 INNOV8 Labs (Lanna, TH)\n\n{tags}"

    variables = {
        "input": {
            "text": description,
            "channelId": profile_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": assets,
            "metadata": {
                "instagram": {
                    "type": "reel" if is_video else "story",
                    "shouldShareToFeed": True if is_video else False
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

        # FLEXIBLE MATCHING (Including Premiere Temp patterns)
        workflow = None
        for key in WORKFLOW_MAP:
            if ext.startswith(key):
                # Create a specific workflow instance with a random label
                base_workflow = WORKFLOW_MAP[key]
                category = base_workflow.get("category", "graphic")
                workflow = {
                    "label": random.choice(LABEL_POOL.get(category, ["Studio Activity"])),
                    "mood": base_workflow["mood"]
                }
                break
        
        # Premiere specific temp handling (Handles files with no extension during save)
        if not workflow and len(ext) == 0:
            try:
                parent_dir = os.path.dirname(file_path)
                if any(f.lower().endswith(".prproj") for f in os.listdir(parent_dir)):
                    workflow = WORKFLOW_MAP.get(".prproj")
            except: pass

        if workflow:
            project_name = get_project_name(file_path)
            
            # --- INTENTION CHECK (Freshness) ---
            # If the modification time is not "Now" (within 5 seconds), 
            # it's likely a move/copy/import, not an active render/save.
            try:
                mtime = os.path.getmtime(file_path)
                if (time.time() - mtime) > 30.0:
                    return
            except: pass

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
        global last_broadcast_time
        try:
            current_time = time.time()
            ext = os.path.splitext(file_path)[1].lower().strip()
            
            # Identify Quality
            is_video = (ext == ".mp4" or ext == ".mov")
            is_audio = (ext in [".wav", ".mp3"])
            is_image = (ext in [".jpg", ".jpeg", ".png"])
            is_high_quality = is_video or is_audio or is_image

            # 0. GLOBAL COOLDOWN (Echo-Zero Lock)
            if current_time - last_broadcast_time < BROADCAST_LOCK_PERIOD:
                return
            
            # 1. PROJECT COOLDOWN & QUALITY FILTER
            cooldown_key = f"{project_name}_{workflow['label']}"
            if cooldown_key in last_sent_cache:
                last_pulse = last_sent_cache[cooldown_key]
                # Handle legacy cache format
                if not isinstance(last_pulse, dict):
                    last_pulse = {"time": last_pulse, "is_high_quality": False}
                
                # If we just sent a high-quality pulse, ignore low-quality ones for 2 minutes
                if last_pulse["is_high_quality"] and not is_high_quality:
                    if current_time - last_pulse["time"] < 120:
                        return
                
                # Standard burst protection
                if current_time - last_pulse["time"] < 15:
                    return
            
            last_sent_cache[cooldown_key] = {"time": current_time, "is_high_quality": is_high_quality}
            last_broadcast_time = current_time
            
            # 1. PREPARE METADATA
            mood = workflow['mood']
            quote = get_random_quote()

            software_map = {
                ".prproj": "Premiere Pro", ".psd": "Photoshop", ".aep": "After Effects",
                ".wav": "Studio Engine", ".mp3": "Studio Engine", ".mp4": "Media Encoder", 
                ".mov": "DaVinci Resolve",
                ".png": "Graphic Engine", ".jpg": "Graphic Engine"
            }
            
            # Smart Software detection for temp files
            software = software_map.get(ext, "Creative Engine")
            if software == "Creative Engine" and workflow['label'] == "Deep in the Edit":
                software = "Premiere Pro"
            
            # Photoshop Heuristics
            if software == "Graphic Engine" or ext in [".jpg", ".png"]:
                try:
                    parent_dir = os.path.dirname(file_path)
                    if any(f.lower().endswith(".psd") for f in os.listdir(parent_dir)):
                        software = "Photoshop"
                    elif "DEER" in project_name.upper():
                        software = "Photoshop"
                except: pass

            # 2. CAPTURE VISION / VIDEO / AUDIO / IMAGE (Synchronous)
            asset_url = ""
            asset_file = None
            if is_video:
                log_msg(f">>> [VIDEO] Extracting highlight from {os.path.basename(file_path)}...")
                asset_file = extract_random_clip(file_path)
            elif is_audio:
                log_msg(f">>> [AUDIO] Generating visualizer for {os.path.basename(file_path)}...")
                asset_file = generate_audio_visualizer(file_path)
            elif is_image:
                # Use the saved image directly!
                log_msg(f">>> [IMAGE] Using saved file as pulse asset: {os.path.basename(file_path)}")
                try:
                    temp_asset = f"image_pulse_{int(time.time())}{ext}"
                    import shutil
                    # Wait a bit for Photoshop to release the file if needed
                    time.sleep(1)
                    shutil.copy2(file_path, temp_asset)
                    asset_file = temp_asset
                except Exception as e:
                    log_msg(f"[IMAGE COPY ERROR] {e}")
            
            if not asset_file:
                asset_file = capture_screenshot()
            
            if asset_file:
                try:
                    with open(asset_file, 'rb') as f:
                        file_ext = os.path.splitext(asset_file)[1]
                        storage_path = f"pulses/{int(time.time())}{file_ext}"
                        supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                        asset_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                except Exception as e:
                    log_msg(f"[IMAGING/VIDEO ERROR] {e}")

            # 3. DISPATCH FULL PULSE TO SUPABASE
            data = {
                "project_name": project_name,
                "action_label": workflow["label"],
                "mood_tag": f"{mood}|Neural link active.|{asset_url}|{software}|{quote}", 
                "source": "Windows-Workstation",
                "is_milestone": (is_video or is_audio or software == "Premiere Pro" or software == "Photoshop")
            }
            
            log_msg(f">>> [SYNC] Dispatching pulse for {project_name} via {software}...")
            res = supabase.table("studio_heartbeat").insert(data).execute()
            
            if res.data:
                log_msg(f">>> [SYNC] SUCCESS! Vision Linked: {asset_url}")
            else:
                log_msg(">>> [SYNC ERROR] Insert failed.")

            # 4. ROUTE TO BUFFER
            buffer_profile = BUFFER_PROFILE_ID_MAIN
            path_upper = file_path.upper()
            proj_upper = project_name.upper()
            
            if "LANNA" in path_upper or "LANNA" in proj_upper:
                buffer_profile = BUFFER_PROFILE_ID_LANNA
            elif any(x in path_upper for x in ["BLUE CHROMATIC", "TRIANGLE", "DEER"]) or any(x in proj_upper for x in ["BLUE", "TRIANGLE", "DEER"]):
                buffer_profile = BUFFER_PROFILE_ID_BLUE

            if is_video or is_audio:
                # VIDEO/AUDIO POST (REELS/SHORTS)
                media_type = "Sound" if is_audio else "Visual"
                msg = f"🔥 New {media_type} Pulse: #{project_name} in progress. #{software} workflow. feed.in-no-v8.com"
                broadcast_to_buffer(msg, profile_id=buffer_profile, asset_url=asset_url, is_video=True, post_type="REEL")
            else:
                # GRID POST (SQUARE 1:1)
                log_msg(f">>> [GRID] Generating square crop for {project_name}...")
                square_file = f"square_{int(time.time())}.jpg"
                try:
                    # FFmpeg 1:1 Square Crop
                    subprocess.run(['ffmpeg', '-y', '-i', asset_file, '-vf', "crop=min(iw\,ih):min(iw\,ih)", square_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with open(square_file, 'rb') as f:
                        storage_path = f"pulses/grid_{int(time.time())}.jpg"
                        supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                        grid_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                    msg = f"◈ STUDIO PHASE: #{project_name} R&D active. #{software} development. feed.in-no-v8.com"
                    broadcast_to_buffer(msg, profile_id=buffer_profile, asset_url=grid_url, is_video=False, post_type="GRID")
                    if os.path.exists(square_file): os.remove(square_file)
                except Exception as e:
                    log_msg(f"[GRID SYNC ERROR] {e}")
                
                # ALSO POST AS STORY (FULL SCREEN SNAPSHOT)
                msg_story = f"◈ LIVE STUDIO PULSE: {project_name} ◈"
                broadcast_to_buffer(msg_story, profile_id=buffer_profile, asset_url=asset_url, is_video=False, post_type="STORY")
                
            # --- FINAL CLEANUP ---
            if asset_file and ("screenshot_" in asset_file or "clip_" in asset_file or "audio_pulse_" in asset_file or "image_pulse_" in asset_file) and os.path.exists(asset_file):
                try:
                    os.remove(asset_file)
                except: pass

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

def generate_blueprint(input_image):
    """Converts a screenshot into a blue/white technical blueprint schematic."""
    try:
        output_file = f"blueprint_temp_{int(time.time())}.jpg"
        # FFmpeg filter: Edge detection -> Negate -> Colorkey over Blue Background
        cmd = [
            'ffmpeg', '-y', '-i', input_image,
            '-filter_complex',
            "[0:v]edgedetect=low=0.1:high=0.4,negate,format=rgba,colorkey=0xffffff:0.1:0.1[fg];"
            "color=c=0x003366:s=1920x1080[bg];"
            "[bg][fg]overlay=format=auto[out]",
            '-map', '[out]', '-frames:v', '1', output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except Exception as e:
        log_msg(f"[BLUEPRINT ERROR] {e}")
        return None

def generate_audio_visualizer(audio_path):
    """Generates a random 10-second vertical waveform video from an audio file."""
    try:
        # 1. Get Duration
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        duration = float(subprocess.check_output(cmd).decode().strip())
        
        if duration < 12:
            start = 0
            t = duration
        else:
            start = random.uniform(2, max(2, duration - 12))
            t = 10
            
        output_file = f"audio_pulse_{int(time.time())}.mp4"
        
        # 2. Generate Waveform Video (Vertical 1080x1920)
        # Using a cyan neon waveform on dark background
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', str(t), '-i', audio_path,
            '-filter_complex', 
            "[0:a]showwaves=s=1080x1920:mode=line:colors=0x00FFB4:draw=full[v]",
            '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
            '-c:a', 'aac', '-b:a', '128k', output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except Exception as e:
        log_msg(f"[AUDIO VIS ERROR] {e}")
        return None

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

# --- DAILY MAINTENANCE TRIGGER ---
def schedule_cleanup():
    """Triggers the cleanup_studio.py script every 24 hours."""
    try:
        log_msg("◈ [MAINTENANCE] Running daily studio cleanup...")
        subprocess.Popen(["python", "cleanup_studio.py"])
    except Exception as e:
        log_msg(f"[MAINTENANCE ERROR] {e}")
    
    # Reschedule for tomorrow
    threading.Timer(86400, schedule_cleanup).start()

if __name__ == "__main__":
    # Startup Scan: Populate last_size_cache to avoid "Open" pulses on first launch
    log_msg("Initializing Studio Pulse Vision Pipeline...")
    load_cache()
    for root, dirs, files in os.walk(WATCH_PATH):
        if any(ignore in root for ignore in IGNORE_FOLDERS): continue
        for f in files:
            ext = os.path.splitext(f)[1].lower().strip()
            if any(key in ext for key in WORKFLOW_MAP):
                path = os.path.join(root, f)
                try: last_size_cache[path] = os.path.getsize(path)
                except: pass
    log_msg(f"Primed {len(last_size_cache)} project files.")

    # Start the maintenance schedule
    schedule_cleanup()

    while True:
        try:
            event_handler = HeartbeatHandler()
            observer = Observer()
            observer.schedule(event_handler, WATCH_PATH, recursive=True)
            observer.start()
            log_msg(f"Monitoring {WATCH_PATH} with Buffer integration and Echo Fix (Active)...")
            
            while observer.is_alive():
                # Self-check pulse in log every hour
                if int(time.time()) % 3600 == 0:
                    log_msg("◈ [STATUS] Heartbeat Active and Monitoring.")
                time.sleep(1)
                
        except Exception as e:
            err_msg = traceback.format_exc()
            log_msg(f"!!! [CRITICAL WATCHER ERROR] {e}\n{err_msg}")
            log_msg("Restarting observer in 10 seconds...")
            try:
                observer.stop()
            except:
                pass
            time.sleep(10)
        except KeyboardInterrupt:
            observer.stop()
            break
            
    observer.join()
