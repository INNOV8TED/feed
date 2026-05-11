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

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# DYNAMIC WATCH PATH: Monitor the parent of the current script location
WATCH_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git", "Auto-Save", "Adobe Premiere Pro Auto-Save"]
IGNORE_FILES = [
    "heartbeat.log", "heartbeat.lock", "heartbeat.py", "test_sync.py", "temp.jpg",
    ".tmp", ".m4v", ".aac", ".prsl", "._00_", "placeholder", "clip_", "audio_pulse_",
    ".pek", ".cfa", ".ims", ".re", "_AME", ".crdownload", ".part"
]
COOLDOWN_SECONDS = 5  # Reduced cooldown
DEBOUNCE_SECONDS = 5.0 # Increased responsiveness
DAILY_BUFFER_LIMIT = 8  # Safe limit for Free Plan
QUOTA_FILE = "buffer_quota.json"
NETWORK_TIMEOUT = 15

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

def broadcast_to_buffer(text, profile_id, asset_url=None, is_video=False, post_type="REEL"):
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

def get_video_dimensions(path):
    """Detect aspect ratio for smart routing."""
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        return int(data['streams'][0]['width']), int(data['streams'][0]['height'])
    except:
        return 1920, 1080 # Default to vertical

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
    
    log_msg(f"◈ [BUFFER] Dispatching {post_type} payload for {profile_id[-4:]}...")
    # log_msg(f"◈ [DEBUG] Variables: {json.dumps(variables)}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BUFFER_TOKEN}"
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
        print(full_msg.encode('ascii', 'ignore').decode('ascii'), flush=True)
    except:
        pass
        
    try:
        with open("heartbeat.log", "a", encoding='utf-8') as f:
            f.write(full_msg + "\n")
            f.flush()
            os.fsync(f.fileno()) # Force write to disk
    except: pass

class HeartbeatHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        # IRON SEAL: Immediate suppression of internal system noise
        if any(f in path for f in IGNORE_FILES + [".git"]):
            return
        
        log_msg(f"[WATCHER] Change Detected: {os.path.basename(event.src_path)}")
        self.process_event(event)
        
    def on_created(self, event):
        if event.is_directory: return
        path = event.src_path.lower()
        if any(f in path for f in ["heartbeat.log", "heartbeat.py", "heartbeat.lock", "test_sync.py", "temp.jpg", ".git"]):
            return
        
        log_msg(f"[WATCHER] Created: {os.path.basename(event.src_path)}")
        self.process_event(event)

    def process_event(self, event):
        try:
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
                        "mood": base_workflow["mood"],
                        "category": category
                    }
                    break
            
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
                    # File is locked by Adobe - skip this event
                    return

                # 2. SIZE STABILITY CHECK
                try:
                    last_size = -1
                    stable_count = 0
                    # Renders need a longer stability window
                    checks = 20 if is_video else 5 
                    
                    for _ in range(checks):
                        current_size = os.path.getsize(file_path)
                        # Filter out empty placeholders (less than 1KB)
                        if current_size == last_size and current_size > 1024:
                            stable_count += 1
                        else:
                            stable_count = 0
                        
                        if stable_count >= 3: break # Stable for ~1.5s after initial growth
                        
                        last_size = current_size
                        time.sleep(0.5)
                        
                    if stable_count < 3:
                        return
                except: return

                project_name = get_project_name(file_path)
                
                # --- INTENTION CHECK (Freshness) ---
                # If the modification time is not "Now" (within 5 seconds), 
                # it's likely a move/copy/import, not an active render/save.
                try:
                    mtime = os.path.getmtime(file_path)
                    ctime = os.path.getctime(file_path)
                    # Use the most recent of modification or creation time
                    freshness = time.time() - max(mtime, ctime)
                    
                    # ASSET LENIENCY: Allow images/videos even if old, unless they are EXTREMELY old (1 week)
                    # OR if they are in the "RANDOM" or "MEMORIES" or "SOCIAL" folder (unlimited age)
                    is_asset = ext in [".png", ".jpg", ".jpeg", ".mp4", ".mov", ".wav", ".mp3"]
                    is_special_folder = any(x in file_path.upper() for x in ["RANDOM", "MEMORIES", "SOCIAL"])
                    
                    if is_special_folder:
                        threshold = 315360000.0 # 10 years (effectively unlimited)
                    else:
                        threshold = 604800.0 if is_asset else 120.0 
                    
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

        except Exception as e:
            log_msg(f"[PROCESS ERROR] {e}")

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

            # 1. PRODUCTION-ONLY FILTER (Video/Audio)
            # Only pulse videos/audio if they are in an output-related folder
            # This prevents stock assets, footage, and source files from triggering pulses.
            path_upper = file_path.upper()
            output_keywords = ["EXPORTS", "MASTERS", "FINAL", "SOCIAL", "MEMORIES", "OUTPUT", "RENDER", "DELIVERABLES", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "[PULSE]"]
            asset_keywords = ["ASSETS", "FOOTAGE", "STOCK", "SOURCE", "RAW", "INGEST", "MATERIAL"]
            
            if is_video or is_audio:
                is_in_output = any(k in path_upper for k in output_keywords)
                is_in_asset = any(k in path_upper for k in asset_keywords) or any(k in path_upper for k in ["IMPORT", "USE", "素材"])
                
                # STRIKE TEAM: If it's not in an explicit output folder, or it's in an asset folder, KILL IT.
                if is_in_asset or not is_in_output:
                    return
                
                # ROOT GUARD: If the file is too shallow in the project (likely an asset drag-and-drop), skip it.
                rel_path = os.path.relpath(file_path, WATCH_PATH)
                is_explicit_pulse = "[PULSE]" in path_upper
                if len(rel_path.split(os.sep)) < 3 and not any(k in path_upper for k in ["SOCIAL", "MEMORIES", "ARCHIVE", "BEST_OF", "HIGHLIGHTS"]) and not is_explicit_pulse:
                    # Likely root-level asset
                    return

            # 2. GLOBAL COOLDOWN (Echo-Zero Lock)
            if current_time - last_broadcast_time < BROADCAST_LOCK_PERIOD:
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
            
            action_label = workflow['label']
            
            # FOLDER-SPECIFIC LOGIC (MEMORIES & SOCIAL)
            path_upper = file_path.upper()
            if "MEMORIES" in path_upper or "SOCIAL" in path_upper:
                # Use filename as label, but clean it up
                filename = os.path.splitext(os.path.basename(file_path))[0]
                # Remove numbers and underscores
                import re
                clean_name = re.sub(r'[\d_]+', ' ', filename).strip()
                # If it's MEMORIES, add location/date context if possible (from folder structure)
                if "MEMORIES" in path_upper:
                    action_label = f"◈ {clean_name}"
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
                        content_type = "video/mp4" if asset_file.endswith(".mp4") else "image/jpeg"
                        if asset_file.endswith(".mov"): content_type = "video/quicktime"
                        if asset_file.endswith(".png"): content_type = "image/png"
                        
                        supabase.storage.from_('studio-assets').upload(
                            storage_path, f.read(), 
                            file_options={"content-type": content_type}
                        )
                        asset_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
                    
                except Exception as e:
                    log_msg(f"[IMAGING/VIDEO ERROR] {e}")

            # 3. CHANNEL IDENTIFICATION (Hierarchical Brand Check)
            channel_id = "INNOV8"
            buffer_profile = BUFFER_PROFILE_ID_MAIN
            path_parts = [p.upper() for p in file_path.split(os.sep)]
            
            if "LANNA" in path_parts:
                channel_id = "LANNA"
                buffer_profile = BUFFER_PROFILE_ID_LANNA
            elif "BLUE" in path_parts or "BLUE CHROMATIC" in path_parts:
                channel_id = "BLUE"
                buffer_profile = BUFFER_PROFILE_ID_BLUE
            elif "INNOV8" in path_parts:
                channel_id = "INNOV8"
                buffer_profile = BUFFER_PROFILE_ID_MAIN

            # 4. DISPATCH FULL PULSE TO SUPABASE (CHANNEL-AWARE)
            is_social_folder = any(k in path_upper for k in ["MEMORIES", "SOCIAL", "ARCHIVE", "BEST_OF", "HIGHLIGHTS", "[PULSE]"])
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
            res = supabase.table("studio_heartbeat").insert(data).execute()
            
            if res.data:
                log_msg(f">>> [SYNC] SUCCESS! Vision Linked: {asset_url}")
            else:
                log_msg(">>> [SYNC ERROR] Insert failed.")

            if is_video or is_audio:
                # DETECT IF SQUARE OR VERTICAL FOR SMART ROUTING
                width, height = get_video_dimensions(file_path)
                is_square = abs(width - height) < (width * 0.1)
                
                target_type = "REEL"
                if is_square: target_type = "GRID"
                
                media_type = "Sound" if is_audio else "Visual"
                msg = f"🔥 New {media_type} Pulse: #{project_name} in progress. #{software} workflow. feed.in-no-v8.com"
                broadcast_to_buffer(msg, profile_id=buffer_profile, asset_url=asset_url, is_video=True, post_type=target_type)
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
                    broadcast_to_buffer(msg, profile_id=buffer_profile, asset_url=grid_url, is_video=False, post_type="GRID")
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
                    broadcast_to_buffer(msg_story, profile_id=buffer_profile, asset_url=story_url, is_video=False, post_type="STORY")
                    if os.path.exists(story_file): os.remove(story_file)
                except Exception as e:
                    log_msg(f"[STORY SYNC ERROR] {e}")
                
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
    """Generates an AI-powered 'Blue Chromatic' lyric video with Vector Scope visuals."""
    try:
        # 1. Get Duration
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
        duration = float(subprocess.check_output(cmd).decode().strip())
        
        t = min(15, duration)
        start = 0 # For lyrics, we usually want the start
            
        output_file = f"audio_pulse_{int(time.time())}.mp4"
        srt_file = f"lyrics_{int(time.time())}.srt"
        
        # 2. AI TRANSCRIPTION (OpenAI Whisper)
        lyrics_text = ""
        if openai_client:
            try:
                log_msg(f">>> [AI] Transcribing {os.path.basename(audio_path)} via Whisper...")
                with open(audio_path, "rb") as audio:
                    # Get transcription in SRT format for burned-in subtitles
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio, 
                        response_format="srt"
                    )
                    with open(srt_file, "w", encoding="utf-8") as f:
                        f.write(transcript)
            except Exception as ai_err:
                log_msg(f"[AI ERROR] {ai_err}")
        
        # 3. Generate Vector Scope Video (Vertical 1080x1920)
        # Filters: Lissajous Vector Scope + Burned-in Subtitles
        # Note: Subtitles filter requires escaping backslashes on Windows
        escaped_srt = srt_file.replace("\\", "/").replace(":", "\\:")
        
        filter_complex = (
            f"[0:a]avectorscope=s=1080x1920:m=lissajous:rc=0:gc=204:bc=255:rf=1:gf=1:bf=1[v];"
        )
        
        # If we have lyrics, burn them in
        if os.path.exists(srt_file):
            filter_complex += f"[v]subtitles='{escaped_srt}':force_style='Alignment=2,FontSize=24,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=120'[v]"
        
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', str(t), '-i', audio_path,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', output_file
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup temp srt
        if os.path.exists(srt_file): os.remove(srt_file)
        
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
    log_msg(f"Initializing Studio Pulse Vision Pipeline... (PID: {os.getpid()})")
    log_msg(f"Watch Path: {WATCH_PATH}")
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

    # Redirect stderr to log for capturing silent crashes (line-buffered)
    sys.stderr = open("heartbeat.log", "a", encoding='utf-8', buffering=1)

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
                # Self-check pulse in log every 2 minutes
                now = int(time.time())
                if now % 120 < 1: # Capture every 2 mins
                    log_msg("◈ [STATUS] Heartbeat Active and Monitoring.")
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
