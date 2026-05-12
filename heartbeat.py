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
import datetime
from dotenv import load_dotenv
import sys
from openai import OpenAI
import shutil
import base64

# Load environment variables with absolute path
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

# --- CONFIGURATION ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI Client
openai_client = None
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI Init Error: {e}")

# --- GLOBAL PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "heartbeat.log")
LOCK_PATH = os.path.join(BASE_DIR, "heartbeat.lock")

# DYNAMIC WATCH PATH: Monitor the parent of the current script location
WATCH_PATH = os.path.dirname(BASE_DIR)
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git", "Auto-Save", "Adobe Premiere Pro Auto-Save", "RECYCLE.BIN"]
IGNORE_FILES = [
    "heartbeat.log", "heartbeat.lock", "heartbeat.py", "test_sync.py", "temp.jpg", "last_log.txt", "log_tail_v2.txt",
    ".tmp", ".m4v", ".aac", ".prsl", "._00_", "placeholder", "clip_", "audio_pulse_", "lyrics_",
    ".pek", ".cfa", ".ims", ".re", "_AME", ".crdownload", ".part", ".log", ".prmdc"
]
COOLDOWN_SECONDS = 5  # Reduced cooldown
DEBOUNCE_SECONDS = 5.0 # Increased responsiveness
DAILY_BUFFER_LIMIT = 8  # Safe limit for Free Plan
QUOTA_FILE = "buffer_quota.json"
NETWORK_TIMEOUT = 15
PENDING_DIR = os.path.join(BASE_DIR, "PENDING_BROADCAST")
for d in ["CAROUSELS", "POSTS"]:
    os.makedirs(os.path.join(PENDING_DIR, d), exist_ok=True)

# Global cache to persist across observer restarts
last_sent_cache = {}
# Persistence Cache
CACHE_FILE = "studio_cache.json"
last_size_cache = {}
fingerprint_cache = {} # Tracks (size, ctime) to prevent renames from pulsing

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
BROADCAST_LOCK_PERIOD = 20
pending_timers = {}
recent_pulse_lock = {} # {path: timestamp} to prevent duplicates

# --- SINGLETON LOCK ---
import msvcrt
lock_file_handle = None

def get_lock():
    try:
        global lock_file_handle
        lock_file_handle = open(LOCK_PATH, "w")
        msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        return True
    except:
        return False

if not get_lock():
    # Only print to console as log might not be ready
    print(f"Another instance of heartbeat.py is already running. (Lock: {LOCK_PATH})")
    exit(0)

if not URL or not KEY:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    exit(1)

# Expanded Label Pool for Variety
LABEL_POOL = {
    "edit":     ["Deep in the Edit", "Cutting the Master", "Timeline Sculpting", "Visual Storytelling", "Assembly Phase", "Edit Lock In Progress", "Color Correction"],
    "motion":   ["Motion Graphics & FX", "Visual Synthesis", "Dynamic Simulation", "After Effects Magic", "Kinetic Design", "FX Pass", "Animating Reality"],
    "graphic":  ["Graphic Design", "Visual Prototyping", "Digital Alchemy", "Aesthetic Refinement", "Composition Phase", "Pixel Perfecting", "Texture Mapping", "Branding Forge"],
    "audio":    ["Audio Mastering", "Sonic Engineering", "Melodic Synthesis", "Frequency Sculpting", "Mixing Session", "Atmospheric Layering", "Rhythm Engine Active"],
    "render":   ["Exporting Master", "Finalizing Visuals", "Rendering Sequence", "Baking Pixels", "Outputting Production", "Encoding Final Cut"],
    "save":     ["Project Save", "Studio Snapshot", "Progress Archiving", "State Captured", "Timeline Sync"]
}

# Mapping file types to categories and moods
WORKFLOW_MAP = {
    ".prproj": {"category": "save",    "mood": "focused"},
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

def generate_and_upload_thumbnail(video_path):
    """Extracts a frame from a video and uploads it as a thumbnail."""
    try:
        temp_thumb = f"thumb_temp_{int(time.time())}.jpg"
        # Extract frame at 5 seconds (to avoid fade-from-black intros)
        cmd = ['ffmpeg', '-y', '-i', video_path, '-ss', '00:00:05', '-vframes', '1', temp_thumb]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(temp_thumb):
            url = upload_to_supabase(temp_thumb, "thumbnails")
            try: os.remove(temp_thumb)
            except: pass
            return url
        return None
    except Exception as e:
        log_msg(f"[THUMB ERROR] {e}")
        return None

def upload_to_supabase(file_path, folder="pulses"):
    """Helper to upload a file to Supabase and return the public URL."""
    try:
        with open(file_path, 'rb') as f:
            file_ext = os.path.splitext(file_path)[1].lower()
            storage_path = f"{folder}/{int(time.time())}_{os.path.basename(file_path)}"
            content_type = "video/mp4" if file_ext == ".mp4" else "image/jpeg"
            if file_ext == ".mov": content_type = "video/quicktime"
            if file_ext == ".png": content_type = "image/png"
            
            supabase.storage.from_('studio-assets').upload(
                storage_path, f.read(), 
                file_options={"content-type": content_type}
            )
            return supabase.storage.from_('studio-assets').get_public_url(storage_path)
    except Exception as e:
        log_msg(f"[SUPABASE UPLOAD ERROR] {e}")
        return None

def insert_pulse_to_supabase(project_name, action_label, asset_url, mood="energetic", software="Studio Engine", quote="", channel_id="INNOV8", is_milestone=True, is_social=False):
    """Helper to insert a pulse record into the Supabase heartbeat table."""
    try:
        status_text = "Social active." if is_social else "Neural link active."
        data = {
            "project_name": project_name,
            "action_label": action_label,
            "mood_tag": f"{mood}|{status_text}|{asset_url}|{software}|{quote}|{channel_id}", 
            "source": "Windows-Workstation",
            "is_milestone": is_milestone
        }
        res = supabase.table("studio_heartbeat").insert(data).execute()
        return res.data
    except Exception as e:
        log_msg(f"[SUPABASE INSERT ERROR] {e}")
        return None

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
        
        # If in root, use the filename itself (without extension)
        return os.path.splitext(os.path.basename(file_path))[0]
    except:
        return "Studio Project"

def broadcast_to_buffer(text, profile_id, asset_urls=None, is_video=False, post_type="REEL", bypass_quota=False, platform="instagram"):
    if not profile_id:
        log_msg("Buffer Profile ID missing. Skipping broadcast.")
        return

    # --- CURATED SCHEDULE: 1 REEL AND 1 GRID POST PER CHANNEL PER DAY ---
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        quota = {}
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, 'r') as f:
                quota = json.load(f)
        
        # Structure: quota[date][profile_id][post_type] = 1
        if today not in quota: quota[today] = {}
        if profile_id not in quota[today]: quota[today][profile_id] = {}
        
        # INCREASED QUOTA: 2 items per type (allows for Today + Tomorrow queue depth)
        if not bypass_quota and quota[today][profile_id].get(post_type, 0) >= 2:
            log_msg(f"◈ [QUOTA] Buffer queue for {post_type} ({profile_id[-4:]}) is sufficiently filled (Today+Tomorrow).")
            return
            
        # Mark as sent
        quota[today][profile_id][post_type] = 1
        with open(QUOTA_FILE, 'w') as f:
            json.dump(quota, f)
    except Exception as e:
        log_msg(f"[QUOTA ERROR] {e}")

    if not BUFFER_TOKEN or "your_buffer" in BUFFER_TOKEN:
        log_msg("Buffer token missing. Skipping broadcast.")
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
    
    # Prepare Assets according to Buffer GraphQL Schema
    assets_payload = {}
    images = []
    videos = []
    
    if asset_urls:
        if isinstance(asset_urls, str): asset_urls = [{"url": asset_urls}]
        for item in asset_urls:
            # item can be a string (URL) or a dict {"url": ..., "thumbnail": ...}
            a_url = item["url"] if isinstance(item, dict) else item
            a_thumb = item.get("thumbnail") if isinstance(item, dict) else None
            
            is_vid = a_url.lower().endswith(('.mp4', '.mov'))
            if is_vid:
                videos.append({
                    "url": a_url, 
                    "thumbnailUrl": a_thumb if a_thumb else f"{a_url}?v=thumb"
                })
            else:
                images.append({"url": a_url})
    
    if images: assets_payload["images"] = images
    if videos: assets_payload["videos"] = videos
    
    if not assets_payload:
        log_msg("No assets for Buffer. Skipping.")
        return

    # Select hashtags based on content
    tags = " #StudioPulse #Innov8Labs #CreativeProcess #NeuralLink"
    if post_type == "GRID" and "MEMORY" in text:
        tags = " #StudioPulse #Memories #Innov8Labs #BehindTheScenes"
    elif is_video: 
        tags += " #Reel #Production"
    else: 
        tags += " #StudioVision #BehindTheScenes"

    # Neural Branding Description
    header = "◈ STUDIO MEMORY ◈" if "MEMORY" in text else "◈ STUDIO BROADCAST ◈"
    description = f"{header}\n\n{text}\n\n📍 INNOV8 Labs (Lanna, TH)\n\n{tags}"

    # --- 2. BUILD PAYLOAD ---
    metadata = {}
    if platform == "youtube":
        metadata = {
            "youtube": {
                "title": text[:100], # Required
                "categoryId": "24"    # Entertainment - Required by Buffer for YT
            }
        }
    else:
        metadata = {
            "instagram": {
                "type": "post" if post_type == "GRID" else ("reel" if is_video else "story"),
                "shouldShareToFeed": True
            }
        }

    variables = {
        "input": {
            "text": description,
            "channelId": profile_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": assets_payload,
            "metadata": metadata
        }
    }
    
    log_msg(f"◈ [BUFFER] Dispatching {post_type} payload for {profile_id[-4:]}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BUFFER_TOKEN}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers, timeout=NETWORK_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                log_msg(f"Buffer GraphQL Error: {data['errors']}")
            else:
                try:
                    post_id = data['data']['createPost']['post']['id']
                    log_msg(f"🚀 Buffer Success! Post created with ID: {post_id} on channel {profile_id}")
                    return True
                except:
                    log_msg(f"Buffer Response Data: {data}")
                    return False
        else:
            log_msg(f"Buffer HTTP error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log_msg(f"Buffer broadcast script error: {e}")
        return False

def get_video_dimensions(path):
    """Detect aspect ratio for smart routing."""
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        return int(data['streams'][0]['width']), int(data['streams'][0]['height'])
    except:
        return 1080, 1920 # Default to vertical (Shorts/Reels)

# --- SUPABASE HARDENING ---
def get_supabase_client():
    try:
        return create_client(URL, KEY)
    except Exception as e:
        print(f"Supabase Client Init Error: {e}")
        return None

supabase = get_supabase_client()

def log_msg(msg):
    """Robust logging with global absolute paths."""
    full_msg = f"[{time.ctime()}] {msg}"
    
    try:
        print(full_msg.encode('ascii', 'ignore').decode('ascii'), flush=True)
    except: pass
        
    try:
        with open(LOG_PATH, "a", encoding='utf-8') as f:
            f.write(full_msg + "\n")
            f.flush()
            os.fsync(f.fileno())
    except: pass

# --- AI ENGINE INITIALIZATION ---
if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        log_msg("◈ [AI SYSTEM] OpenAI Engine Initialized.")
    except Exception as e:
        log_msg(f"◈ [AI SYSTEM ERROR] Initialization failed: {e}")
else:
    log_msg("◈ [AI SYSTEM] Warning: OPENAI_API_KEY not found in .env")

def convert_image_to_video(image_path):
    """Converts a static image into a 3-second MP4 video for carousel compatibility."""
    try:
        ts = int(time.time())
        output_file = os.path.join(os.path.dirname(image_path), f"vid_{ts}_{random.randint(100,999)}.mp4")
        # Create a 3s loop of the image. Scale to even dimensions for H.264
        cmd = [
            'ffmpeg', '-y', '-loop', '1', '-i', image_path, 
            '-c:v', 'libx264', '-t', '3', '-pix_fmt', 'yuv420p', 
            '-vf', "scale='if(gt(iw,ih),1080,-2)':'if(gt(iw,ih),-2,1080)',pad=1080:1080:(1080-iw)/2:(1080-ih)/2:black,format=yuv420p",
            output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except Exception as e:
        log_msg(f"[IMG->VID ERROR] {e}")
        return None

class HeartbeatHandler(FileSystemEventHandler):
    def __init__(self):
        self.is_primed = False

    def on_modified(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        basename = os.path.basename(path)
        
        # IRON SEAL: Global Ignore Checks
        if any(folder.lower() in path for folder in IGNORE_FOLDERS): return
        if any(ign.lower() in basename for ign in IGNORE_FILES): return
        
        ext = os.path.splitext(path)[1].lower().strip()
        if ext in IGNORE_FILES or ".git" in path:
            return
            
        log_msg(f"◈ [WATCHER] Change Detected: {basename}")
        self.process_event(event)
        
    def on_created(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        basename = os.path.basename(path)

        # IRON SEAL: Global Ignore Checks
        if any(folder.lower() in path for folder in IGNORE_FOLDERS): return
        if any(ign.lower() in basename for ign in IGNORE_FILES): return

        ext = os.path.splitext(path)[1].lower().strip()
        if ext in IGNORE_FILES or ".git" in path:
            return
        
        log_msg(f"◈ [WATCHER] Created: {basename}")
        self.process_event(event)

    def on_moved(self, event):
        if event.is_directory: return
        path = event.dest_path.lower()
        basename = os.path.basename(path)

        # IRON SEAL: Global Ignore Checks
        if any(folder.lower() in path for folder in IGNORE_FOLDERS): return
        if any(ign.lower() in basename for ign in IGNORE_FILES): return

        ext = os.path.splitext(path)[1].lower().strip()
        if ext in IGNORE_FILES or ".git" in path:
            return
        
        log_msg(f"[WATCHER DEBUG] Event Moved: {event.dest_path}")
        log_msg(f"[WATCHER] Moved: {basename}")
        self.process_event(event)

    def process_event(self, event):
        try:
            # CORRECT PATH DETECTION (Handle Moves)
            file_path = event.dest_path if hasattr(event, 'dest_path') else event.src_path
            ext = os.path.splitext(file_path)[1].lower().strip()
                
            # DEEP DEBUG
            log_msg(f"[DEBUG] Ext Seen: '{ext}' | Map Type: {type(WORKFLOW_MAP)}")

            # FLEXIBLE MATCHING (Including Premiere Temp patterns)
            workflow = None
            for key in WORKFLOW_MAP:
                log_msg(f"◈ [DEBUG] Testing Key: '{key}' against '{ext}'")
                if ext.startswith(key):
                    # Create a specific workflow instance with a random label
                    base_workflow = WORKFLOW_MAP[key]
                    category = base_workflow.get("category", "graphic")
                    workflow = {
                        "label": random.choice(LABEL_POOL.get(category, ["Studio Activity"])),
                        "mood": base_workflow["mood"],
                        "category": category
                    }
                    break
            log_msg(f"◈ [DEBUG] Workflow Found: {workflow is not None} (Category: {workflow.get('category') if workflow else 'None'})")
            
            # Premiere specific temp handling (Handles files with no extension during save)
            if not workflow and len(ext) == 0:
                try:
                    parent_dir = os.path.dirname(file_path)
                    if any(f.lower().endswith(".prproj") for f in os.listdir(parent_dir)):
                        base_workflow = WORKFLOW_MAP.get(".prproj")
                        category = base_workflow.get("category", "save")
                        workflow = {
                            "label": random.choice(LABEL_POOL.get(category, ["Studio Snapshot"])),
                            "mood": base_workflow["mood"],
                            "category": category
                        }
                except: pass

            if workflow:
                # --- ACTIVE INTENTION CHECK (Stability & Locking) ---
                # 1. EXCLUSIVE LOCK CHECK (Windows Render Guard)
                # If Media Encoder is rendering, it has a write-lock.
                try:
                    # Attempt to open the file exclusively for appending
                    # If this fails, the file is busy (Active Render)
                    with open(file_path, 'a'):
                        pass
                except (IOError, OSError):
                    # File is locked - skip this event
                    log_msg(f"◈ [WATCHER] Busy: {os.path.basename(file_path)} (Locked by another process)")
                    return

                # 2. SIZE STABILITY CHECK
                # Lanna Carousel Check (Subfolder in LANNA)
                # Structure: .../LANNA/Subfolder/file.ext
                path_parts = file_path.replace("\\", "/").split("/")
                is_carousel = False
                if "LANNA" in [p.upper() for p in path_parts]:
                    # CAROUSEL CHECK: It's a carousel ONLY if it's in a SUBFOLDER of LANNA
                    parent_dir = os.path.dirname(file_path)
                    if os.path.basename(parent_dir).upper() != "LANNA":
                        carousel_folder = parent_dir
                        is_carousel = True
                        log_msg(f"◈ [CAROUSEL] Detected potential component: {os.path.basename(file_path)}")
                
                # STABILITY CHECK
                last_size = -1
                stable_count = 0
                while True:
                    time.sleep(2)
                    try:
                        if not os.path.exists(file_path): return
                        current_size = os.path.getsize(file_path)
                        
                        if current_size == last_size and current_size > 0:
                            stable_count += 1
                        else:
                            stable_count = 0
                        
                        if stable_count >= 3: break # 6 seconds stability
                        last_size = current_size
                    except: 
                        return
                
                if is_carousel:
                    # Wait for the WHOLE FOLDER to be stable (no new files or modifications)
                    log_msg(f"◈ [CAROUSEL] Waiting for folder stability: {os.path.basename(carousel_folder)}")
                    try:
                        folder_last_mtime = os.path.getmtime(carousel_folder)
                        while True:
                            time.sleep(5)
                            current_mtime = os.path.getmtime(carousel_folder)
                            if current_mtime == folder_last_mtime:
                                break
                            folder_last_mtime = current_mtime
                        
                        # One more safety sleep
                        time.sleep(2)
                        self.dispatch_carousel(carousel_folder)
                    except: pass
                    return

                project_name = get_project_name(file_path)
                
                # --- INTENTION CHECK (Freshness) ---
                # If the modification time is not "Now" (within 5 seconds), 
                # it's likely a move/copy/import, not an active render/save.
                try:
                    mtime = os.path.getmtime(file_path)
                    ctime = os.path.getctime(file_path)
                    # Use the most recent of modification or creation time
                    freshness = time.time() - max(mtime, ctime)
                    
                    # ASSET LENIENCY: Allow images/videos even if old, unless they are EXTREMELY old (60 days)
                    # OR if they are in the "RANDOM" or "MEMORIES" or "SOCIAL" folder (unlimited age)
                    is_asset = ext in [".png", ".jpg", ".jpeg", ".mp4", ".mov", ".wav", ".mp3"]
                    is_special_folder = any(x in file_path.upper() for x in ["RANDOM", "MEMORIES", "SOCIAL", "LANNA"])
                    
                    if is_special_folder or self.is_primed:
                        threshold = 315360000.0 # 10 years (effectively unlimited)
                    else:
                        threshold = 5184000.0 if is_asset else 120.0 # 60 days for assets, 2 mins for projects
                    
                    if freshness > threshold:
                        log_msg(f"◈ [WATCHER] Skipping {os.path.basename(file_path)}: File is too old ({int(freshness)}s).")
                        return
                except: pass

                # --- OPEN VS SAVE FILTER ---
                try:
                    current_size = os.path.getsize(file_path)
                    last_size = last_size_cache.get(file_path)
                    
                    # If it's a project file (not a render/asset) and size hasn't changed, ignore it.
                    # This prevents "Open" events from triggering pulses.
                    is_media = ext in [".mp4", ".mov", ".mp3", ".wav", ".jpg", ".png"]
                    is_social = any(k in file_path.upper() for k in ["SOCIAL", "MEMORIES", "[PULSE]", "ARCHIVE"])
                    
                    if not is_media and not is_social and last_size is not None and current_size == last_size:
                        log_msg(f"◈ [WATCHER] Skipping {os.path.basename(file_path)}: Size unchanged ({current_size} bytes).")
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
                
                # Cleanup finished timers periodically
                if len(pending_timers) > 50:
                    finished = [k for k, t in pending_timers.items() if not t.is_alive()]
                    for k in finished: del pending_timers[k]

        except BaseException as e:
            import traceback
            err_msg = traceback.format_exc()
            log_msg(f"◈ [CRITICAL PROCESS ERROR] {type(e).__name__}: {e}\n{err_msg}")

    def dispatch_carousel(self, folder_path):
        """Processes a folder as a single carousel post."""
        try:
            # 1. Check Weekly Quota
            current_week = datetime.datetime.now().strftime('%Y-%W')
            quota_data = {}
            if os.path.exists(QUOTA_FILE):
                try:
                    with open(QUOTA_FILE, 'r') as f:
                        quota_data = json.load(f)
                except: pass
            
            if quota_data.get("weekly_lanna_carousel_sent") == current_week:
                log_msg(f"◈ [QUOTA] Weekly Lanna Carousel already sent. Moving {os.path.basename(folder_path)} to Pending.")
                try:
                    target = os.path.join(PENDING_DIR, "CAROUSELS", os.path.basename(folder_path))
                    if os.path.exists(target): shutil.rmtree(target)
                    shutil.move(folder_path, target)
                except Exception as e: log_msg(f"[QUEUE ERROR] {e}")
                return
            
            # 1. Folder Stability Wait
            # (Using 5s sleep to ensure all files in batch moves are accounted for)
            time.sleep(5)
            
            # RE-CHECK QUOTA AFTER WAIT (Crucial for batch moves to prevent race conditions)
            try:
                with open(QUOTA_FILE, 'r') as f:
                    q_check = json.load(f)
                if q_check.get("weekly_lanna_carousel_sent") == current_week:
                    log_msg(f"◈ [QUOTA] Weekly Lanna Carousel filled during wait. Skipping {os.path.basename(folder_path)}")
                    return
            except: pass

            # 2. Gather All Media
            valid_exts = [".jpg", ".png", ".mp4", ".mov"]
            media_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in valid_exts]
            
            if not media_files:
                return
            
            log_msg(f">>> [CAROUSEL] Dispatching {len(media_files)} items from {os.path.basename(folder_path)}...")
            
            # 3. Gather and Normalize Media
            asset_data = []
            temp_files = []
            
            # Check if we have mixed media
            has_video = any(f.lower().endswith(('.mp4', '.mov')) for f in media_files)
            has_image = any(f.lower().endswith(('.jpg', '.png', '.jpeg')) for f in media_files)
            is_mixed = has_video and has_image
            
            if is_mixed:
                log_msg(f">>> [CAROUSEL] Mixed media detected. Normalizing photos to video segments for unified feed...")
            
            for f in sorted(media_files): # Ensure order
                is_vid = f.lower().endswith(('.mp4', '.mov'))
                
                active_file = f
                if is_mixed and not is_vid:
                    # Convert image to 3s video to allow mixed carousel
                    optimized_vid = convert_image_to_video(f)
                    if optimized_vid:
                        active_file = optimized_vid
                        temp_files.append(optimized_vid)
                        is_vid = True
                
                url = upload_to_supabase(active_file, "pulses")
                if url:
                    item = {"url": url}
                    if is_vid:
                        thumb = generate_and_upload_thumbnail(active_file)
                        if thumb: item["thumbnail"] = thumb
                    asset_data.append(item)
            
            if not asset_data: return
            
            # 4. Dispatch Unified Carousel
            folder_name = os.path.basename(folder_path)
            msg = f"◈ LANNA WHISPERS: {folder_name} (Collection) ◈"
            
            # Sync to Website
            insert_pulse_to_supabase("Lanna Whispers", "Collection", asset_data[0]["url"], channel_id="LANNA", is_social=True)
            
            # Broadcast to Buffer
            # If we normalized everything, is_video must be True to trigger Video Carousel logic in Buffer
            force_video = is_mixed or has_video
            success = broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_LANNA, asset_urls=asset_data, is_video=force_video, post_type="GRID", bypass_quota=True)
            
            if success:
                quota_data["weekly_lanna_carousel_sent"] = current_week
                with open(QUOTA_FILE, 'w') as f:
                    json.dump(quota_data, f)
                log_msg(f">>> [CAROUSEL SUCCESS] {folder_name} unified and live.")
            
            # Cleanup temp videos
            for tf in temp_files:
                try: os.remove(tf)
                except: pass
            
        except Exception as e:
            log_msg(f"[CAROUSEL ERROR] {e}")

    def dispatch_heartbeat(self, project_name, workflow, file_path):
        """The actual logic that sends data to Supabase, after debounces."""
        global last_broadcast_time
        try:
            current_time = time.time()
            
            # 1. DUPLICATION GUARD (Session Lock)
            if file_path in recent_pulse_lock:
                if current_time - recent_pulse_lock[file_path] < 600: # 10 Minute Lock
                    return
            recent_pulse_lock[file_path] = current_time
            
            ext = os.path.splitext(file_path)[1].lower().strip()
            is_video = ext in [".mp4", ".mov"]
            is_audio = ext in [".mp3", ".wav"]
            
            # Identify Quality
            is_video = (ext == ".mp4" or ext == ".mov")
            is_audio = (ext in [".wav", ".mp3"])
            is_image = (ext in [".jpg", ".jpeg", ".png"])
            is_high_quality = is_video or is_audio or is_image

            # 1. PRODUCTION-ONLY FILTER (Video/Audio)
            # Only pulse videos/audio if they are in an output-related folder
            # This prevents stock assets, footage, and source files from triggering pulses.
            path_upper = file_path.upper()
            output_keywords = ["EXPORTS", "MASTERS", "FINAL", "SOCIAL", "MEMORIES", "OUTPUT", "RENDER", "DELIVERABLES", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "[PULSE]", "PROCESSED", "RELEASED", "PODCAST", "EPISODES"]
            asset_keywords = ["ASSETS", "FOOTAGE", "STOCK", "SOURCE", "RAW", "INGEST", "MATERIAL"]
            
            if is_video or is_audio:
                rel_path_upper = os.path.relpath(file_path, WATCH_PATH).upper()
                log_msg(f"◈ [DEBUG] Checking Pulse: {rel_path_upper}")
                is_in_output = any(k in rel_path_upper for k in output_keywords)
                is_in_asset = any(k in rel_path_upper for k in asset_keywords) or any(k in rel_path_upper for k in ["/IMPORT", "/USE", "\\IMPORT", "\\USE"])
                
                # STRIKE TEAM: Allow root-level media, or anything in an explicit output folder.
                # But KILL anything in an asset folder.
                is_root = os.path.dirname(file_path) == WATCH_PATH
                if is_in_asset: return
                if not is_in_output and not is_root:
                    return
                
                # ROOT GUARD: If the file is too shallow in the project (likely an asset drag-and-drop), skip it.
                rel_path = os.path.relpath(file_path, WATCH_PATH)
                is_explicit_pulse = "[PULSE]" in path_upper
                if len(rel_path.split(os.sep)) < 3 and not any(k in path_upper for k in ["SOCIAL", "MEMORIES", "ARCHIVE", "BEST_OF", "HIGHLIGHTS"]) and not is_explicit_pulse:
                    # Likely root-level asset
                    return

            # 2. GLOBAL COOLDOWN (Echo-Zero Lock)
            # BYPASS for specialized social releases
            is_special_social = any(k in path_upper for k in ["MEMORIES", "BLUE"])
            if not is_special_social and (current_time - last_broadcast_time < BROADCAST_LOCK_PERIOD):
                return
            
            # 3. DIGITAL FINGERPRINT CHECK (Rename/Move Guard)
            # Prevent re-pulsing if the file was just renamed or moved
            try:
                f_size = os.path.getsize(file_path)
                f_ctime = os.path.getctime(file_path)
                fingerprint = f"{f_size}_{f_ctime}"
                
                if fingerprint in fingerprint_cache:
                    # We've seen this exact file content/state before
                    return
                
                # Store fingerprint
                fingerprint_cache[fingerprint] = current_time
                
                # Periodic cleanup of old fingerprints (older than 24h)
                if len(fingerprint_cache) > 500:
                    cutoff = current_time - 86400
                    expired = [k for k, v in fingerprint_cache.items() if v < cutoff]
                    for k in expired: del fingerprint_cache[k]
            except: pass

            # 2. FILE-PATH COOLDOWN (Echo-Zero Lock)
            # Use the absolute path as the key to prevent echos for the same file
            cooldown_key = file_path
            
            if cooldown_key in last_sent_cache:
                last_pulse = last_sent_cache[cooldown_key]
                
                # High-quality pulses (videos) have a much longer cooldown for the same file
                # Standard render takes time; we only want one pulse per 10 mins for the same file
                if is_video and current_time - last_pulse["time"] < 600: 
                    return
                
                # Standard burst protection for everything else (15s)
                if not is_video and current_time - last_pulse["time"] < 15:
                    return
            
            last_sent_cache[cooldown_key] = {"time": current_time, "is_high_quality": is_high_quality}
            last_broadcast_time = current_time
            
            # 1. PREPARE METADATA
            mood = workflow['mood']
            quote = get_random_quote()
            # Identify Action Label
            action_label = workflow["label"]
            
            # AI CAPTION UPGRADE (For Social/Lanna Posts)
            is_social_folder = any(k in path_upper for k in ["MEMORIES", "SOCIAL", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "LANNA", "LABS", "[PULSE]"])
            if openai_client and (is_social_folder or "LANNA" in path_upper) and not is_audio:
                ai_caption = generate_visual_caption(file_path)
                if ai_caption:
                    action_label = ai_caption

            # FOLDER-SPECIFIC LOGIC (MEMORIES & SOCIAL)
            path_upper = file_path.upper()
            if "MEMORIES" in path_upper or "SOCIAL" in path_upper:
                # Use filename as label, but clean it up
                filename = os.path.splitext(os.path.basename(file_path))[0]
                # Remove numbers and underscores
                import re
                clean_name = re.sub(r'[\d_]+', ' ', filename).strip()
                
                if "MEMORIES" in path_upper:
                    action_label = f"◈ {clean_name}"
                    
                    # EXTRACT NUMERICAL INDEX (e.g. "1 - Title" -> 1)
                    try:
                        match = re.search(r'^(\d+)', filename)
                        file_index = int(match.group(1)) if match else None
                    except: file_index = None

                    # WEEKLY & SEQUENTIAL QUOTA CHECK
                    current_week = datetime.datetime.now().strftime('%Y-%W')
                    quota_data = {}
                    if os.path.exists(QUOTA_FILE):
                        try:
                            with open(QUOTA_FILE, 'r') as f:
                                quota_data = json.load(f)
                        except: pass
                    
                    last_index = quota_data.get("last_memory_index", 0)
                    
                    if quota_data.get("weekly_memory_sent") == current_week:
                        log_msg(f"◈ [QUOTA] Weekly Memory already sent for week {current_week}. Skipping {os.path.basename(file_path)}")
                        return

                    if file_index is not None and file_index != last_index + 1:
                        log_msg(f"◈ [QUOTA] Memory #{file_index} is out of sequence. Next expected: #{last_index + 1}")
                        return
                elif "BLUE" in path_upper:
                    action_label = f"◈ BLUE: {clean_name}"
                    
                    # WEEKLY QUOTA CHECK
                    current_week = datetime.datetime.now().strftime('%Y-%W')
                    quota_data = {}
                    if os.path.exists(QUOTA_FILE):
                        try:
                            with open(QUOTA_FILE, 'r') as f:
                                quota_data = json.load(f)
                        except: pass
                    
                    if quota_data.get("weekly_blue_sent") == current_week:
                        log_msg(f"◈ [QUOTA] Weekly Blue release already sent for week {current_week}. Skipping {os.path.basename(file_path)}")
                        return
                elif "LABS" in path_upper:
                    action_label = f"◈ LABS: {clean_name}"
                    
                    # WEEKLY QUOTA CHECK
                    current_week = datetime.datetime.now().strftime('%Y-%W')
                    quota_data = {}
                    if os.path.exists(QUOTA_FILE):
                        try:
                            with open(QUOTA_FILE, 'r') as f:
                                quota_data = json.load(f)
                        except: pass
                    
                    if quota_data.get("weekly_labs_sent") == current_week:
                        log_msg(f"◈ [QUOTA] Weekly Labs release already sent for week {current_week}. Skipping {os.path.basename(file_path)}")
                        return
                else:
                    action_label = clean_name

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

            is_social_folder = any(k in path_upper for k in ["MEMORIES", "SOCIAL", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "LANNA", "LABS", "[PULSE]"])

            # 2. CAPTURE VISION / VIDEO / AUDIO / IMAGE (Synchronous)
            asset_url = ""
            asset_file = None
            is_video = ext in ['.mp4', '.mov']
            is_audio = ext in ['.wav', '.mp3']
            is_image = ext in ['.jpg', '.jpeg', '.png']
            is_social_folder = any(k in path_upper for k in ["MEMORIES", "SOCIAL", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "LANNA", "LABS", "[PULSE]"])

            # --- OPTIMIZATION PASS (Social Only) ---
            active_source = file_path
            is_temp_optimized = False
            if is_social_folder:
                optimized = optimize_media(file_path)
                if optimized != file_path:
                    active_source = optimized
                    is_temp_optimized = True

            if is_video:
                log_msg(f">>> [VIDEO] Extracting highlight from {os.path.basename(active_source)}...")
                asset_file = extract_random_clip(active_source)
            elif is_audio:
                log_msg(f">>> [AUDIO] Generating visualizer for {os.path.basename(active_source)}...")
                is_song = "BLUE" in path_upper
                asset_file = generate_audio_visualizer(active_source, is_song=is_song)
            elif is_image:
                log_msg(f">>> [IMAGE] Preparing pulse asset: {os.path.basename(active_source)}")
                try:
                    temp_asset = f"image_pulse_{int(time.time())}{os.path.splitext(active_source)[1]}"
                    import shutil
                    time.sleep(1)
                    shutil.copy2(active_source, temp_asset)
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
                        content_type = "video/mp4" if asset_file.endswith(".mp4") else "image/jpeg"
                        if asset_file.endswith(".mov"): content_type = "video/quicktime"
                        if asset_file.endswith(".png"): content_type = "image/png"
                        
                        supabase.storage.from_('studio-assets').upload(
                            storage_path, f.read(), 
                            file_options={"content-type": content_type}
                        )
                        asset_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                        
                        # 2nd Upload for Social (Using optimized version if available)
                        full_asset_url = asset_url 
                        if is_social_folder:
                            try:
                                log_msg(f">>> [SOCIAL] Uploading optimized source for Buffer...")
                                # Special Case: For Audio, we need to generate a FULL visualizer for Social
                                actual_social_source = active_source
                                is_temp_full_audio = False
                                if is_audio:
                                    log_msg(f">>> [SOCIAL] Generating FULL-LENGTH visualizer for Buffer...")
                                    is_song = "BLUE" in path_upper
                                    actual_social_source = generate_audio_visualizer(active_source, full_length=True, is_song=is_song)
                                    is_temp_full_audio = True

                                full_storage_path = f"social/{int(time.time())}_full{os.path.splitext(actual_social_source)[1]}"
                                
                                # GENERATE THUMBNAIL FOR SOCIAL (Video & Audio)
                                social_thumb = None
                                if is_audio or is_video:
                                    social_thumb = generate_and_upload_thumbnail(actual_social_source)

                                with open(actual_social_source, 'rb') as f_full:
                                    supabase.storage.from_('studio-assets').upload(
                                        full_storage_path, f_full.read(),
                                        file_options={"content-type": content_type if not is_audio else "video/mp4"}
                                    )
                                full_asset_url = supabase.storage.from_('studio-assets').get_public_url(full_storage_path)
                                
                                # Wrap in dict for Buffer if we have a thumb
                                if social_thumb:
                                    full_asset_data = {"url": full_asset_url, "thumbnail": social_thumb}
                                else:
                                    full_asset_data = full_asset_url
                                
                                # Cleanup temp full audio visualizer
                                if is_temp_full_audio and os.path.exists(actual_social_source):
                                    try: os.remove(actual_social_source)
                                    except: pass
                            except Exception as e:
                                log_msg(f"[SOCIAL UPLOAD ERROR] {e}")
                    
                except Exception as e:
                    log_msg(f"[IMAGING/VIDEO ERROR] {e}")

            # CLEANUP OPTIMIZED TEMP
            if is_temp_optimized and os.path.exists(active_source):
                try: os.remove(active_source)
                except: pass

            # 3. CHANNEL IDENTIFICATION (Hierarchical Brand Check)
            channel_id = "INNOV8"
            buffer_profile = BUFFER_PROFILE_ID_MAIN
            # Robust split handling both \ and /
            path_parts = [p.upper() for p in file_path.replace("\\", "/").split("/")]
            
            if "LANNA" in path_parts:
                channel_id = "LANNA"
                buffer_profile = BUFFER_PROFILE_ID_LANNA
            elif "BLUE" in path_parts or "BLUE CHROMATIC" in path_parts:
                channel_id = "BLUE"
                buffer_profile = BUFFER_PROFILE_ID_BLUE
            elif "INNOV8" in path_parts:
                channel_id = "INNOV8"
                buffer_profile = BUFFER_PROFILE_ID_MAIN

            # 4. PRE-SYNC QUOTA CHECK FOR LANNA (Prevent Website Spam)
            if channel_id == "LANNA" and is_social_folder:
                try:
                    width, height = get_video_dimensions(file_path)
                    is_vert = height > width
                    q_type = ("REEL" if is_video else "STORY") if is_vert else "GRID"
                    
                    today = datetime.datetime.now().strftime('%Y-%m-%d')
                    if os.path.exists(QUOTA_FILE):
                        with open(QUOTA_FILE, 'r') as f:
                            q_data = json.load(f)
                        if q_data.get(today, {}).get(buffer_profile, {}).get(q_type, 0) >= 1:
                            log_msg(f"◈ [QUOTA] Lanna Daily full. Moving {os.path.basename(file_path)} to Pending.")
                            try:
                                target = os.path.join(PENDING_DIR, "POSTS", os.path.basename(file_path))
                                shutil.move(file_path, target)
                            except Exception as e: log_msg(f"[QUEUE ERROR] {e}")
                            return
                except: pass

            # 4. DISPATCH FULL PULSE TO SUPABASE (CHANNEL-AWARE)
            status_text = "Social active." if is_social_folder else "Neural link active."
            # Data structure: mood|status|url|software|quote|channel_id
            data = {
                "project_name": project_name,
                "action_label": action_label,
                "mood_tag": f"{mood}|{status_text}|{asset_url}|{software}|{quote}|{channel_id}", 
                "source": "Windows-Workstation",
                "is_milestone": (is_video or is_audio or software == "Premiere Pro" or software == "Photoshop")
            }
            
            log_msg(f">>> [SYNC] Dispatching pulse for {project_name} via {software} (Channel: {channel_id})...")
            if insert_pulse_to_supabase(
                project_name=project_name,
                action_label=action_label,
                asset_url=asset_url,
                mood=mood,
                software=software,
                quote=quote,
                channel_id=channel_id,
                is_milestone=(is_video or is_audio or software == "Premiere Pro" or software == "Photoshop"),
                is_social=is_social_folder
            ):
                log_msg(f">>> [SYNC] SUCCESS! Vision Linked: {asset_url}")
            else:
                log_msg(">>> [SYNC ERROR] Insert failed.")

            if "MEMORIES" in path_upper or "BLUE" in path_upper or "LABS" in path_upper or "LANNA" in path_upper:
                # SPECIALIZED BROADCAST (Main Feed, Once a Week)
                log_msg(f">>> [SOCIAL RELEASE] Dispatching weekly pulse to Buffer...")
                
                # Update weekly quota (before broadcast to ensure lock)
                try:
                    quota_data = {}
                    if os.path.exists(QUOTA_FILE):
                        with open(QUOTA_FILE, 'r') as f:
                            quota_data = json.load(f)
                    
                    current_week = datetime.datetime.now().strftime('%Y-%W')
                    
                    if "MEMORIES" in path_upper:
                        quota_data["weekly_memory_sent"] = current_week
                        # Update sequence index
                        try:
                            import re
                            filename = os.path.splitext(os.path.basename(file_path))[0]
                            match = re.search(r'^(\d+)', filename)
                            if match:
                                quota_data["last_memory_index"] = int(match.group(1))
                        except: pass
                    elif "BLUE" in path_upper:
                        quota_data["weekly_blue_sent"] = current_week
                    elif "LABS" in path_upper:
                        quota_data["weekly_labs_sent"] = current_week

                    with open(QUOTA_FILE, 'w') as f:
                        json.dump(quota_data, f)
                except: pass

                # Buffer Dispatch (Main Grid Post) - BYPASS DAILY QUOTA for weekly special
                msg = f"{action_label}"
                asset_is_video = asset_url.lower().endswith(('.mp4', '.mov'))
                
                if "MEMORIES" in path_upper:
                    broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_MAIN, asset_urls=[full_asset_url], is_video=asset_is_video, post_type="GRID", bypass_quota=True)
                elif "BLUE" in path_upper:
                    if is_audio:
                        width, height = 1080, 1920
                    else:
                        width, height = get_video_dimensions(file_path)
                        
                    is_vertical = height > width
                    is_square = abs(width - height) < (width * 0.1)
                    
                    if is_vertical:
                        # 1. YouTube Blue (Shorts)
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_BLUE, asset_urls=[full_asset_data], is_video=True, post_type="REEL", bypass_quota=True, platform="youtube")
                        # 2. Instagram Main (Reels)
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_MAIN, asset_urls=[full_asset_data], is_video=True, post_type="REEL", bypass_quota=True, platform="instagram")
                    elif is_square:
                        # 1. Instagram Main (Grid Post)
                        thumb = generate_and_upload_thumbnail(active_source) if asset_is_video else None
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_MAIN, asset_urls=[{"url": full_asset_url, "thumbnail": thumb}], is_video=asset_is_video, post_type="GRID", bypass_quota=True, platform="instagram")
                elif "LABS" in path_upper:
                    # LABS SPECIAL ROUTING (Instagram Only)
                    width, height = get_video_dimensions(file_path)
                    is_vertical = height > width
                    
                    if is_vertical:
                        target_type = "REEL" if is_video else "STORY"
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_MAIN, asset_urls=[full_asset_url], is_video=is_video, post_type=target_type, bypass_quota=True)
                    else:
                        # Square/Horizontal
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_MAIN, asset_urls=[full_asset_url], is_video=is_video, post_type="GRID", bypass_quota=True)
                elif "LANNA" in path_upper:
                    # LANNA SPECIAL ROUTING (Daily Quota applies)
                    width, height = get_video_dimensions(file_path)
                    is_vertical = height > width
                    
                    if is_vertical:
                        target_type = "REEL" if is_video else "STORY"
                        thumb = generate_and_upload_thumbnail(active_source) if is_video else None
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_LANNA, asset_urls=[{"url": full_asset_url, "thumbnail": thumb}], is_video=is_video, post_type=target_type, bypass_quota=False)
                    else:
                        # Square/Horizontal
                        thumb = generate_and_upload_thumbnail(active_source) if is_video else None
                        broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_LANNA, asset_urls=[{"url": full_asset_url, "thumbnail": thumb}], is_video=is_video, post_type="GRID", bypass_quota=False)
                
            elif is_video or is_audio:
                # DETECT IF SQUARE OR VERTICAL FOR SMART ROUTING
                width, height = get_video_dimensions(file_path)
                is_square = abs(width - height) < (width * 0.1)
                
                target_type = "REEL"
                if is_square: target_type = "GRID"
                
                media_type = "Sound" if is_audio else "Visual"
                msg = f"🔥 New {media_type} Pulse: #{project_name} in progress. #{software} workflow. feed.in-no-v8.com"
                # GENERATE THUMBNAIL FOR PULSE
                thumb = generate_and_upload_thumbnail(asset_file) if (is_video or is_audio) else None
                broadcast_to_buffer(msg, profile_id=buffer_profile, asset_urls=[{"url": asset_url, "thumbnail": thumb}] if thumb else [asset_url], is_video=True, post_type=target_type)
            else:
                # GRID POST (SQUARE 1:1)
                log_msg(f">>> [GRID] Generating square crop for {project_name}...")
                square_file = f"square_{int(time.time())}.jpg"
                try:
                    # FFmpeg 1:1 Square Crop
                    subprocess.run(['ffmpeg', '-y', '-i', asset_file, '-vf', r"crop=min(iw\,ih):min(iw\,ih)", square_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with open(square_file, 'rb') as f:
                        storage_path = f"pulses/grid_{int(time.time())}.jpg"
                        supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                        grid_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                    msg = f"◈ STUDIO PHASE: #{project_name} R&D active. #{software} development. feed.in-no-v8.com"
                    broadcast_to_buffer(msg, profile_id=buffer_profile, asset_urls=[grid_url], is_video=False, post_type="GRID")
                    if os.path.exists(square_file): os.remove(square_file)
                except Exception as e:
                    log_msg(f"[GRID SYNC ERROR] {e}")
                
                # ALSO POST AS STORY (VERTICAL 9:16 SNAPSHOT)
                log_msg(f">>> [STORY] Generating vertical crop for {project_name}...")
                story_file = f"story_{int(time.time())}.jpg"
                try:
                    # FFmpeg 9:16 Vertical Crop (Center)
                    subprocess.run(['ffmpeg', '-y', '-i', asset_file, '-vf', r"scale=w=-1:h=1920,crop=1080:1920", story_file], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with open(story_file, 'rb') as f:
                        storage_path = f"pulses/story_{int(time.time())}.jpg"
                        supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                        story_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                    msg_story = f"◈ LIVE STUDIO PULSE: {project_name} ◈"
                    broadcast_to_buffer(msg_story, profile_id=buffer_profile, asset_urls=[story_url], is_video=False, post_type="STORY")
                    if os.path.exists(story_file): os.remove(story_file)
                except Exception as e:
                    log_msg(f"[STORY SYNC ERROR] {e}")
                
            # --- FINAL CLEANUP ---
            # Don't delete if it's the original file!
            if asset_file and asset_file != file_path and ("screenshot_" in asset_file or "clip_" in asset_file or "audio_pulse_" in asset_file or "image_pulse_" in asset_file) and os.path.exists(asset_file):
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

def generate_audio_visualizer(audio_path, full_length=False, is_song=True):
    """Generates an AI-powered visualizer. Songs get lyrics/vectorscope, others get waveforms."""
    try:
        # 1. Get Duration
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        try:
            duration = float(subprocess.check_output(cmd).decode().strip())
        except:
            duration = 30.0 # Fallback
            
        if is_song:
            t = duration if full_length else min(25, duration)
        else:
            t = min(10, duration) # 10s for podcasts/clients
        
        start = 0 
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ts = int(time.time())
        output_file = os.path.join(base_dir, f"audio_pulse_{ts}.mp4")
        srt_file = os.path.join(base_dir, f"lyrics_{ts}.srt")
        
        # 2. AI TRANSCRIPTION (OpenAI Whisper) - ONLY FOR SONGS
        has_lyrics = False
        if is_song and openai_client:
            try:
                log_msg(f">>> [AI] Transcribing song: {os.path.basename(audio_path)} via Whisper...")
                with open(audio_path, "rb") as audio:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio, 
                        response_format="srt"
                    )
                    if transcript and len(transcript.strip()) > 50: 
                        with open(srt_file, "w", encoding="utf-8") as f:
                            f.write(transcript)
                        has_lyrics = True
                        log_msg(f">>> [AI] Transcription Complete.")
                    else:
                        log_msg(">>> [AI] Transcription empty/short.")
            except Exception as ai_err:
                log_msg(f"[AI ERROR] {ai_err}")
        
        # 3. Generate Visuals (Vertical 1080x1920)
        escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:")
        
        if is_song:
            # Blue Chromatic Vector Scope
            filter_complex = f"[0:a]avectorscope=s=1080x1920:m=lissajous:rc=0:gc=255:bc=255:rf=1:gf=1:bf=1[v];"
            if has_lyrics and os.path.exists(srt_file):
                filter_complex += f"[v]subtitles='{escaped_srt}':force_style='FontName=Arial Black,Alignment=10,FontSize=20,OutlineColour=&H80000000,BorderStyle=1,Outline=1,Shadow=1,MarginV=0'[v]"
            else:
                filter_complex += f"[v]drawtext=text='INSTRUMENTAL PULSE':font='Arial Black':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:alpha=0.6:box=1:boxcolor=black@0.4:boxborderw=20[v]"
        else:
            # Green Peak Waveform for Podcasts/Clients
            filter_complex = f"[0:a]showwaves=s=1080x1920:mode=cline:colors=0x00FF00[v];"
            filter_complex += f"[v]drawtext=text='STUDIO AUDIO LOG':font='Arial':fontcolor=0x00FF00:fontsize=48:x=(w-text_w)/2:y=100:alpha=0.8:box=1:boxcolor=black@0.6:boxborderw=20[v]"
        
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', str(t), '-i', audio_path,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', output_file
        ]
        
        log_msg(f">>> [RENDER] Executing FFmpeg for Music Visualizer (Duration: {t}s)...")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup temp srt
        if os.path.exists(srt_file): 
            try: os.remove(srt_file)
            except: pass
        
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
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(base_dir, f"clip_{int(time.time())}.mp4")
        
        # 3. Extract 10s clip
        # Detect if we should crop to vertical or keep square
        width, height = get_video_dimensions(video_path)
        is_square = abs(width - height) < (width * 0.1) # Within 10% of 1:1
        
        vf = "scale=w=-1:h=1920,crop=1080:1920"
        if is_square:
            # If square, just scale to 1080x1080 (standard Insta Grid size)
            vf = "scale=1080:1080"
            
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', '10', '-i', video_path,
            '-vf', vf,
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '30', 
            '-profile:v', 'baseline', '-level', '3.0',
            '-movflags', '+faststart',
            '-c:a', 'aac', '-b:a', '96k', output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except Exception as e:
        log_msg(f"[CLIP ERROR] {e}")
        return None

def generate_visual_caption(file_path):
    """Uses GPT-4o to analyze the media and generate a descriptive caption."""
    if not openai_client: return None
    
    try:
        # 1. Prepare Image (If video, take a screenshot first)
        temp_img = file_path
        is_vid = file_path.lower().endswith(('.mp4', '.mov'))
        
        if is_vid:
            temp_img = f"ai_temp_{int(time.time())}.jpg"
            cmd = ['ffmpeg', '-y', '-i', file_path, '-ss', '00:00:01', '-vframes', '1', temp_img]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        # 2. Encode to Base64
        with open(temp_img, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        # 3. Call GPT-4o
        log_msg(f">>> [AI] Analyzing visual context for {os.path.basename(file_path)}...")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this studio work in 5-8 words for a professional social media feed. Focus on the mood and technical aspect. No hashtags. Example: 'Refining atmospheric lighting in the Lanna temple.'"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=50,
        )
        
        caption = response.choices[0].message.content.strip().strip('"')
        
        # Cleanup
        if is_vid and os.path.exists(temp_img): os.remove(temp_img)
        
        return caption
    except Exception as e:
        log_msg(f"[AI CAPTION ERROR] {e}")
        return None

def optimize_media(file_path):
    """Optimizes media for web/social (compression, resizing, transcoding)."""
    try:
        ext = os.path.splitext(file_path)[1].lower().strip()
        is_vid = ext in ['.mp4', '.mov']
        is_img = ext in ['.jpg', '.jpeg', '.png']
        
        if not is_vid and not is_img: return file_path
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(base_dir, f"optimized_{int(time.time())}{ext if is_vid else '.jpg'}")
        
        if is_vid:
            log_msg(f">>> [OPTIMIZE] Transcoding video for web: {os.path.basename(file_path)}")
            # Resize to 1080p max, CRF 28 (Good balance), AAC Audio
            # We use force_original_aspect_ratio to maintain vertical/square/etc
            cmd = [
                'ffmpeg', '-y', '-i', file_path,
                '-vf', "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease,pad='ceil(iw/2)*2':'ceil(ih/2)*2'",
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                output_file
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            log_msg(f">>> [OPTIMIZE] Compressing image: {os.path.basename(file_path)}")
            # Resize to 1920px max, 80% quality
            cmd = [
                'ffmpeg', '-y', '-i', file_path,
                '-vf', "scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
                '-q:v', '4', # Roughly 80% quality
                output_file
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        if os.path.exists(output_file):
            return output_file
        return file_path
    except Exception as e:
        log_msg(f"[OPTIMIZE ERROR] {e}")
        return file_path

def sync_status_to_supabase():
    """Syncs the current quota and queue status to a special system record in Supabase."""
    try:
        current_week = datetime.datetime.now().strftime('%Y-%W')
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        quota_data = {}
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, 'r') as f: quota_data = json.load(f)
            
        queue_counts = {
            "posts": len(os.listdir(os.path.join(PENDING_DIR, "POSTS"))),
            "carousels": len(os.listdir(os.path.join(PENDING_DIR, "CAROUSELS")))
        }
        
        status_data = {
            "quota": quota_data.get(today, {}),
            "weekly": {
                "lanna": quota_data.get("weekly_lanna_carousel_sent") == current_week,
                "memory": quota_data.get("weekly_memory_sent") == current_week
            },
            "queue": queue_counts,
            "last_heartbeat": int(time.time())
        }
        
        # Use a special pulse for system status
        insert_pulse_to_supabase(
            project_name="[SYSTEM_STATUS]",
            action_label="Telemetry Broadcast",
            asset_url="",
            mood="telemetry",
            software="Watchdog Engine",
            quote=json.dumps(status_data), # Store full JSON in quote
            channel_id="SYSTEM",
            is_milestone=False,
            is_social=False
        )
    except Exception as e:
        log_msg(f"[STATUS SYNC ERROR] {e}")

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

def process_backlog(handler):
    """Checks the PENDING_BROADCAST directory and releases items if quota is available."""
    try:
        current_week = datetime.datetime.now().strftime('%Y-%W')
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 1. Check Carousels
        carousel_pending = sorted([os.path.join(PENDING_DIR, "CAROUSELS", d) for d in os.listdir(os.path.join(PENDING_DIR, "CAROUSELS"))], key=os.path.getmtime)
        if carousel_pending:
            quota_data = {}
            if os.path.exists(QUOTA_FILE):
                with open(QUOTA_FILE, 'r') as f: quota_data = json.load(f)
            if quota_data.get("weekly_lanna_carousel_sent") != current_week:
                folder = carousel_pending[0]
                log_msg(f"◈ [BACKLOG] Releasing Carousel: {os.path.basename(folder)}")
                # Move back to LANNA to process naturally
                dest = os.path.join(WATCH_PATH, "SOCIAL", "LANNA", os.path.basename(folder))
                if os.path.exists(dest): shutil.rmtree(dest)
                shutil.move(folder, dest)
                handler.dispatch_carousel(dest)

        # 2. Check Daily Posts
        posts_pending = sorted([os.path.join(PENDING_DIR, "POSTS", f) for f in os.listdir(os.path.join(PENDING_DIR, "POSTS"))], key=os.path.getmtime)
        for post_path in posts_pending:
            # Determine type
            is_vid = post_path.lower().endswith(('.mp4', '.mov'))
            width, height = get_video_dimensions(post_path)
            is_vert = height > width
            q_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
            
            quota_data = {}
            if os.path.exists(QUOTA_FILE):
                with open(QUOTA_FILE, 'r') as f: quota_data = json.load(f)
            
            if quota_data.get(today, {}).get(BUFFER_PROFILE_ID_LANNA, {}).get(q_type, 0) < 2:
                log_msg(f"◈ [BACKLOG] Releasing {q_type} for tomorrow's queue: {os.path.basename(post_path)}")
                dest = os.path.join(WATCH_PATH, "SOCIAL", "LANNA", os.path.basename(post_path))
                shutil.move(post_path, dest)
                break
        
        # 3. INVENTORY CHECK (Supply Advice)
        inventory_counts = {
            "posts": len(os.listdir(os.path.join(PENDING_DIR, "POSTS"))),
            "carousels": len(os.listdir(os.path.join(PENDING_DIR, "CAROUSELS")))
        }
        if inventory_counts["posts"] == 0 and inventory_counts["carousels"] == 0:
            log_msg("◈ [ADVICE] Social inventory is EMPTY. Feed replenishment required.")
            insert_pulse_to_supabase(
                project_name="[SYSTEM_ADVICE]",
                action_label="Supply Chain Alert: Content Depleted",
                asset_url="",
                mood="warning",
                software="Inventory Watcher",
                quote="The social broadcast queue is dry. New content required in SOCIAL/LANNA or MEMORIES folders to maintain daily momentum.",
                channel_id="SYSTEM",
                is_milestone=False
            )

    except Exception as e:
        log_msg(f"[BACKLOG ERROR] {e}")
    
    # Reschedule Backlog Check every hour (3600 seconds)
    threading.Timer(3600, lambda: process_backlog(handler)).start()

if __name__ == "__main__":
    # Startup Scan: Populate last_size_cache to avoid "Open" pulses on first launch
    log_msg(f"Initializing Studio Pulse Vision Pipeline... (PID: {os.getpid()})")
    log_msg(f"Watch Path: {WATCH_PATH}")
    load_cache()
    log_msg(f"[STARTUP] Absolute Watch Path: {os.path.abspath(WATCH_PATH)}")
    for root, dirs, files in os.walk(WATCH_PATH):
        if any(ignore in root for ignore in IGNORE_FOLDERS): continue
        for f in files:
            ext = os.path.splitext(f)[1].lower().strip()
            if any(key in ext for key in WORKFLOW_MAP):
                path = os.path.join(root, f)
                try: last_size_cache[path] = os.path.getsize(path)
                except: pass
    log_msg(f"Primed {len(last_size_cache)} project files.")

    # Redirect stderr to log for capturing silent crashes (line-buffered)
    sys.stderr = open("heartbeat.log", "a", encoding='utf-8', buffering=1)

    # Start the maintenance schedule
    schedule_cleanup()
    
    # Initial Backlog Check
    event_handler = HeartbeatHandler()
    process_backlog(event_handler)
    sync_status_to_supabase()

    while True:
        try:
            event_handler = HeartbeatHandler()
            observer = Observer()
            observer.schedule(event_handler, WATCH_PATH, recursive=True)
            observer.start()
            event_handler.is_primed = True
            log_msg(f"Monitoring {WATCH_PATH} with Buffer integration and Echo Fix (Active)...")
            
            while observer.is_alive():
                # Self-check pulse in log every 2 minutes
                now = int(time.time())
                if now % 120 < 1: # Capture every 2 mins
                    log_msg("◈ [STATUS] Heartbeat Active and Monitoring.")
                    process_backlog(event_handler)
                    sync_status_to_supabase()
                    time.sleep(1) # Prevent double logging
                time.sleep(1)
                
        except BaseException as e:
            err_msg = traceback.format_exc()
            log_msg(f"!!! [CRITICAL WATCHER ERROR] {type(e).__name__}: {e}\n{err_msg}")
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
