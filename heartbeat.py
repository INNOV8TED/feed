import os
import sys

# Set working directory to the script's directory to ensure relative paths resolve correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import time
import re
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
import uuid
import datetime
from dotenv import load_dotenv
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
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

# Initialize Resend
import resend
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

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
    global last_size_cache, fingerprint_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and "size_cache" in data:
                    last_size_cache = data.get("size_cache", {})
                    fingerprint_cache = data.get("fingerprints", {})
                    global last_inventory_alert_time
                    last_inventory_alert_time = data.get("last_diagnostic_date", "")
                else:
                    last_size_cache = data # Legacy support
            log_msg(f"◈ [CACHE] Loaded {len(last_size_cache)} states and {len(fingerprint_cache)} fingerprints.")
        except:
            last_size_cache = {}
            fingerprint_cache = {}

def save_cache():
    try:
        data = {
            "size_cache": last_size_cache,
            "fingerprints": fingerprint_cache,
            "last_diagnostic_date": last_inventory_alert_time
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

# Cache loaded in main

# ECHO-ZERO LOCK
last_broadcast_time = 0
last_inventory_alert_time = 0
BROADCAST_LOCK_PERIOD = 20
pending_timers = {}
recent_pulse_lock = {} # {path: timestamp} to prevent duplicates

# Singleton handles
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

def generate_and_upload_thumbnail(video_path, local_only=False):
    """Extracts a frame from a video and uploads it as a thumbnail or returns local path."""
    try:
        unique_id = uuid.uuid4().hex[:8]
        temp_thumb = f"thumb_temp_{unique_id}.jpg"
        # Extract thumbnail at 2 seconds
        cmd = ['ffmpeg', '-y', '-i', video_path, '-ss', '00:00:02', '-vframes', '1', temp_thumb]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        
        if os.path.exists(temp_thumb):
            if local_only:
                return temp_thumb
            url = upload_to_supabase(temp_thumb, "thumbnails")
            try: os.remove(temp_thumb)
            except: pass
            return url
        return None
    except Exception as e:
        log_msg(f"[THUMB ERROR] {e}")
        return None

def upload_to_supabase(file_path, folder="pulses"):
    """Helper to upload a file to Hostgator FTP and return the public HTTP URL with retry handling."""
    import ftplib
    import time
    
    FTP_HOST = "ftp.in-no-v8.com"
    FTP_USER = "innov8co"
    FTP_PASS = "%odn*fr*l4a7$e"
    
    file_ext = os.path.splitext(file_path)[1].lower()
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{unique_id}_{os.path.basename(file_path)}"
    
    max_retries = 5
    retry_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            # Connect to Hostgator FTP
            ftp = ftplib.FTP_TLS(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            
            # Build path: /in-no-v8.world/vault/studio-assets/{folder}
            remote_dir = f"/in-no-v8.world/vault/studio-assets/{folder}"
            
            # Ensure remote directory exists
            parts = remote_dir.split('/')
            current = ""
            for part in parts:
                if not part:
                    continue
                current = f"{current}/{part}"
                try:
                    ftp.mkd(current)
                except Exception:
                    pass
                    
            # Upload the file
            remote_path = f"{remote_dir}/{filename}"
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
                
            ftp.quit()
            
            public_url = f"https://in-no-v8.world/vault/studio-assets/{folder}/{filename}"
            log_msg(f"◈ [FTP UPLOAD SUCCESS] {file_path} -> {public_url}")
            return public_url
            
        except Exception as e:
            err_str = str(e)
            log_msg(f"◈ [FTP UPLOAD ATTEMPT {attempt+1}/{max_retries} FAILED] {file_path}: {err_str}")
            if "421" in err_str or "too many connections" in err_str.lower():
                time.sleep(retry_delay * (attempt + 1))
            else:
                time.sleep(retry_delay)
                
    log_msg(f"◈ [FTP UPLOAD FATAL ERROR] Failed to upload {file_path} after {max_retries} attempts.")
    return None

def insert_pulse_to_supabase(project_name, action_label, asset_url, mood="creative", software="Neural Engine", channel_id="INNOV8", is_social=False, is_milestone=True, quote=""):
    """Unified helper to push heartbeat pulses to both 'studio_heartbeat' and 'feed' tables."""
    status_text = "Social active." if is_social else "Neural link active."
    heartbeat_data = {
        "project_name": project_name,
        "action_label": action_label,
        "mood_tag": f"{mood}|{status_text}|{asset_url}|{software}|{quote}|{channel_id}", 
        "source": "Windows-Workstation",
        "is_milestone": is_milestone
    }
    
    # 1. Sync to World Portal (studio_heartbeat)
    try:
        supabase.table("studio_heartbeat").insert(heartbeat_data).execute()
        log_msg(f"◈ [DB SYNC] Pulse synchronized to studio_heartbeat: {project_name} -> {action_label}")
    except Exception as e:
        log_msg(f"!!! [DB SYNC ERROR - studio_heartbeat] {e}")
        
    # 2. Sync to Web Feed (feed)
    try:
        feed_data = {
            "project_name": project_name,
            "action_label": action_label,
            "asset_url": asset_url,
            "mood": mood,
            "software": software,
            "channel_id": channel_id,
            "is_social": is_social,
            "timestamp": datetime.datetime.now().isoformat()
        }
        supabase.table("feed").insert(feed_data).execute()
        log_msg(f"◈ [DB SYNC] Pulse synchronized to feed: {project_name} -> {action_label}")
    except Exception as e:
        log_msg(f"!!! [DB SYNC ERROR - feed] {e}")

    # 3. Push static JSON snapshot to FTP so WORLD portal has zero Supabase egress
    try:
        import threading as _th
        _th.Thread(target=_push_heartbeat_json_to_ftp, args=(heartbeat_data,), daemon=True).start()
    except Exception as e:
        log_msg(f"!!! [FTP JSON SYNC ERROR] {e}")

def _push_heartbeat_json_to_ftp(new_pulse=None):
    """Fetches latest 20 heartbeat pulses and pushes as studio_heartbeat.json to FTP."""
    try:
        import ftplib, io, json as _json, time
        pulses = []
        
        # Connect to Hostgator FTP
        ftp = ftplib.FTP_TLS("ftp.in-no-v8.com")
        ftp.login("innov8co", "%odn*fr*l4a7$e")
        ftp.prot_p()
        
        # 1. Attempt to download existing studio_heartbeat.json from FTP to maintain history
        try:
            r_bio = io.BytesIO()
            ftp.retrbinary("RETR /in-no-v8.world/vault/studio_heartbeat.json", r_bio.write)
            r_bio.seek(0)
            data_str = r_bio.read().decode("utf-8")
            pulses = _json.loads(data_str)
            if not isinstance(pulses, list):
                pulses = []
        except Exception:
            # Fallback to querying Supabase if FTP file is missing or invalid
            try:
                result = supabase.table("studio_heartbeat") \
                    .select("*") \
                    .neq("project_name", "[SYSTEM_STATUS]") \
                    .order("created_at", desc=True) \
                    .limit(20) \
                    .execute()
                if result.data:
                    pulses = result.data
            except Exception:
                pass

        # 2. If new_pulse is provided, prepend and merge it to the history carefully to preserve telemetry and real pulses
        if new_pulse:
            new_pulse_id = int(time.time())
            new_row = {
                "id": new_pulse_id,
                "project_name": new_pulse.get("project_name"),
                "action_label": new_pulse.get("action_label"),
                "mood_tag": new_pulse.get("mood_tag"),
                "source": new_pulse.get("source"),
                "is_milestone": new_pulse.get("is_milestone"),
                "created_at": datetime.datetime.now().isoformat()
            }
            
            # Determine if this new pulse is a system status telemetry update
            is_telemetry = new_pulse.get("project_name") == "[SYSTEM_STATUS]"
            
            # Separate existing real pulses and existing telemetry pulses
            real_pulses = [p for p in pulses if p.get("project_name") != "[SYSTEM_STATUS]"]
            telemetry_pulses = [p for p in pulses if p.get("project_name") == "[SYSTEM_STATUS]"]
            
            if is_telemetry:
                # Replace with the latest telemetry pulse
                telemetry_pulses = [new_row]
            else:
                # Prepend the new real pulse to the real history
                real_pulses = [new_row] + [p for p in real_pulses if p.get("id") != new_pulse_id]
                
            # Limit the real pulses to the latest 20 items
            real_pulses = real_pulses[:20]
            
            # Combine them: latest telemetry + 20 real pulses
            pulses = telemetry_pulses + real_pulses

        if not pulses:
            ftp.quit()
            return
            
        # 3. Write back to FTP
        json_bytes = _json.dumps(pulses, default=str).encode("utf-8")
        bio = io.BytesIO(json_bytes)
        ftp.storbinary("STOR /in-no-v8.world/vault/studio_heartbeat.json", bio)
        ftp.quit()
        
        kb = len(json_bytes) / 1024
        count = len(pulses)
        log_msg(f"◈ [FTP] studio_heartbeat.json pushed successfully ({kb:.1f} KB, {count} pulses)")
    except Exception as e:
        log_msg(f"[FTP HEARTBEAT JSON ERROR] {e}")

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

def broadcast_to_buffer(text, profile_id, asset_urls=None, is_video=False, post_type="REEL", bypass_quota=False, platform="instagram", location_name=None):
    if not profile_id:
        log_msg("Buffer Profile ID missing. Skipping broadcast.")
        return

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
            
            if not a_url:
                log_msg("◈ [BUFFER] Asset URL is missing. Skipping this item.")
                continue
            
            # YouTube conversion: If it's an image and platform is youtube, we need to convert it
            # But wait, this is a URL. We need the local file path to convert.
            # Actually, it's better to handle this BEFORE calling broadcast_to_buffer if possible.
            # But for robustness, I'll add a check here.
            
            is_vid = a_url.lower().endswith(('.mp4', '.mov'))
            if is_vid:
                videos.append({
                    "url": a_url, 
                    "thumbnailUrl": a_thumb if a_thumb else f"{a_url}?v=thumb"
                })
            else:
                if platform == "youtube":
                    log_msg("◈ [BUFFER] YouTube does not support images. Skipping this asset.")
                    continue
                images.append({"url": a_url})
    
    if images: assets_payload["images"] = images
    if videos: assets_payload["videos"] = videos
    
    if not assets_payload:
        log_msg("No assets for Buffer (or filtered out). Skipping.")
        return False

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
    loc_text = location_name if location_name else "INNOV8 Labs (Lanna, TH)"
    description = f"{header}\n\n{text}\n\n📍 {loc_text}\n\n{tags}"

    # --- 2. BUILD PAYLOAD ---
    metadata = {}
    if platform == "youtube":
        metadata = {
            "youtube": {
                "title": text[:100], # Required
                "categoryId": "24",    # Entertainment - Required by Buffer for YT
                "privacy": "public"
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
            
            # Check for root-level GraphQL errors
            if "errors" in data:
                err_msg = str(data["errors"])
                if 'match the channel service "youtube"' in err_msg and platform != "youtube":
                    log_msg("◈ [BUFFER] Platform mismatch detected in root errors. Retrying as YouTube...")
                    return broadcast_to_buffer(text, profile_id, asset_urls, is_video, post_type, bypass_quota, platform="youtube")
                log_msg(f"Buffer GraphQL Error: {data['errors']}")
                return False

            # Check for logical errors in the mutation response
            create_post_res = data.get('data', {}).get('createPost', {})
            if "message" in create_post_res:
                err_msg = create_post_res["message"]
                if 'match the channel service "youtube"' in err_msg and platform != "youtube":
                    log_msg("◈ [BUFFER] Platform mismatch detected in mutation response. Retrying as YouTube...")
                    return broadcast_to_buffer(text, profile_id, asset_urls, is_video, post_type, bypass_quota, platform="youtube")
                log_msg(f"Buffer Mutation Error: {err_msg}")
                return False
            
            try:
                post_id = create_post_res.get('post', {}).get('id')
                if post_id:
                    log_msg(f"🚀 Buffer Success! Post created with ID: {post_id} on channel {profile_id}")
                    return True
                else:
                    log_msg(f"Buffer Response Data (No ID): {data}")
                    return False
            except Exception as e:
                log_msg(f"Error parsing Buffer success response: {e}")
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

def generate_creative_title(filename):
    """Uses AI to turn generic filenames into evocative studio titles."""
    if not openai_client: return filename
    try:
        # Clean the filename
        clean_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
        
        # Remove common system patterns (dates, hex codes, keywords)
        import re
        stripped = re.sub(r'\d+', '', clean_name).strip()
        if len(stripped) < 3: # Mostly numbers/noise
             pass # Force AI help
             
        log_msg(f"◈ [AI] Requesting title for: {clean_name}")
             
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a creative director. Turn generic video filenames into 2-5 word evocative, professional studio titles. No quotes. No hashtags. Just the title. If it's already a good title, just clean it up."},
                {"role": "user", "content": f"Filename: {clean_name}"}
            ],
            max_tokens=20
        )
        title = response.choices[0].message.content.strip().replace('"', '')
        return title
    except Exception as e:
        # Better fallback naming for when AI is unavailable or quota is exceeded
        prefixes = ["Studio", "Neural", "Digital", "Master", "Creative", "Visual"]
        suffixes = ["Focus", "Flow", "Pulse", "Synthesis", "Logic", "Session"]
        
        # Clean up filename for a semi-decent title
        base = filename.replace("_", " ").replace("-", " ").title()
        import random
        # Only add prefixes if it's a generic looking name
        if any(x in filename.lower() for x in ["render", "output", "export", "save"]):
            return f"{random.choice(prefixes)} {random.choice(suffixes)}"
        
        return base

def send_email_alert(subject, message):
    """Sends a high-priority email alert via Resend."""
    if not RESEND_API_KEY: return
    try:
        params = {
            "from": "Studio Heartbeat <alerts@in-no-v8.com>", 
            "to": ["stephen@in-no-v8.com", "stephen.portman@gmail.com"],
            "subject": subject,
            "html": f"""
            <div style="font-family: sans-serif; background: #050505; color: #fff; padding: 40px; border: 1px solid #00ffaa; border-radius: 8px;">
                <h1 style="color: #00ffaa; margin-top: 0;">◈ STUDIO SUPPLY ALERT</h1>
                <p style="font-size: 1.1em;">{message}</p>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0;">
                <p style="font-size: 0.8em; opacity: 0.5;">This is an automated diagnostic from your Studio Pulse engine.</p>
            </div>
            """
        }
        resend.Emails.send(params)
        log_msg(f"◈ [EMAIL] Alert sent to stephen@in-no-v8.com: {subject}")
    except Exception as e:
        log_msg(f"[EMAIL ERROR] {e}")

def generate_visual_caption(image_path):
    """Uses OpenAI Vision to describe the content of a workflow snapshot."""
    if not openai_client: return None
    try:
        # 1. Prepare Image
        import base64
        ext = os.path.splitext(image_path)[1].lower()
        is_extracted = False
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            # If video, extract middle frame
            image_path = generate_and_upload_thumbnail(image_path, local_only=True)
            if not image_path: return None
            is_extracted = True
            
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        if is_extracted:
            try: os.remove(image_path)
            except: pass
        
        # 2. OpenAI Vision Call
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in 3-5 evocative words. No punctuation. Professional studio tone. Focus on mood or subject."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ],
                }
            ],
            max_tokens=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log_msg(f"[AI VISION ERROR] {e}")
        return None


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
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        return output_file
    except Exception as e:
        log_msg(f"[IMG->VID ERROR] {e}")
        return None

def format_video_vertical(input_path):
    """Ensures video is vertical (1080x1920) using blurry background padding."""
    try:
        width, height = get_video_dimensions(input_path)
        if height > width: return input_path # Already vertical
        
        unique_id = uuid.uuid4().hex[:8]
        output_file = f"vertical_{unique_id}.mp4"
        log_msg(f"◈ [VERTICAL] Formatting {os.path.basename(input_path)} for Reels (1080x1920)...")
        
        # FFmpeg: Blurry background padding to 9:16
        # 1. Scale background to fill 1080x1920 and blur
        # 2. Scale foreground to fit inside 1080x1920
        # 3. Overlay foreground on background
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', (
                "split[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg_blurred];"
                "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg_scaled];"
                "[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2"
            ),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', # Ensure audio is AAC for social
            output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        return output_file
    except Exception as e:
        log_msg(f"[VERTICAL CONVERSION ERROR] {e}")
        return input_path

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
            basename = os.path.basename(file_path)
                
            # --- SEQUENCE GUARD: Block individual frames from PNG/JPG sequences (e.g., _0001.png) ---
            if ext in ['.png', '.jpg']:
                # Refined Regex: Look for trailing frame numbers like _0001 or .0001
                # Must be at least 3 digits but <= 6 digits (to avoid blocking timestamps)
                match = re.search(r'[\._ -](\d{3,})\.', basename) or re.search(r'^(\d{4,})\.', basename)
                if match:
                    digits = match.group(1)
                    if len(digits) <= 6:
                        log_msg(f"◈ [WATCHER] Sequence detected: {basename}. Skipping individual frame to prevent feed flood.")
                        return
                
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
                # 1. GLOBAL CACHE CHECK (History Guard)
                # If we're in startup scan mode, we only pulse if the file is genuinely new to our index.
                f_size = os.path.getsize(file_path)
                f_mtime = os.path.getmtime(file_path)
                cache_key = f"{f_size}_{f_mtime}"
                
                if last_size_cache.get(file_path) == cache_key:
                    if not self.is_primed:
                        # Skip already indexed files during startup
                        log_msg(f">>> [HISTORY GUARD] Skipping already indexed file: {os.path.basename(file_path)}")
                        return
                    # In real-time mode, if nothing changed, skip
                    return
                
                # Determine if file is a media asset that requires lock/render/stability guard
                is_media = ext in [".mp4", ".mov", ".mp3", ".wav", ".jpg", ".png", ".jpeg"]
                is_carousel = False
                carousel_folder = None

                if is_media:
                    # 2. EXCLUSIVE LOCK CHECK (Windows Render Guard)
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

                # 3. SIZE STABILITY CHECK (Only for media assets)
                if is_media:
                    path_parts = file_path.replace("\\", "/").split("/")
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
                        threshold = 5184000.0 if is_asset else 86400.0 # 60 days for assets, 24 hours for projects
                    
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

    def dispatch_heartbeat(self, project_name, workflow, file_path):
        try:
            basename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower().strip()
            is_vid = ext in [".mp4", ".mov"]
            
            # 1. SMART ROUTING & ORIENTATION CHECK
            width, height = get_video_dimensions(file_path) if is_vid else (1080, 1920) # Assume vertical for images
            is_vert = height > width
            is_strict_vertical_video = is_vid and width == 1080 and height == 1920
            
            # Default Profile
            profile_id = BUFFER_PROFILE_ID_MAIN
            channel_id = "INNOV8"
            
            # Specific folder routing
            path_upper = file_path.upper()
            if "LANNA" in path_upper:
                profile_id = BUFFER_PROFILE_ID_LANNA
                channel_id = "LANNA"
            elif "BLUE" in path_upper:
                if is_strict_vertical_video:
                    profile_id = BUFFER_PROFILE_ID_BLUE
                    channel_id = "BLUE"
                else:
                    log_msg(f"◈ [ROUTING] Blue asset {basename} is not a 1080x1920 video. Routing to INN.OV8 instead.")
                    profile_id = BUFFER_PROFILE_ID_MAIN
                    channel_id = "INNOV8"

            # Upload to Supabase first so both portal and feed have the asset
            asset_url = upload_to_supabase(file_path)
            if not asset_url:
                log_msg(f"◈ [HEARTBEAT] Failed to upload {basename} to Supabase. Skipping further dispatch.")
                return

            # Update cache with combined key only AFTER successful upload!
            try:
                f_size = os.path.getsize(file_path)
                f_mtime = os.path.getmtime(file_path)
                cache_key = f"{f_size}_{f_mtime}"
                last_size_cache[file_path] = cache_key
                save_cache()
            except Exception as e:
                log_msg(f"◈ [CACHE ERROR] Failed to save cache: {e}")

            # Check if this asset is inside a 'PUBLISH' subfolder to qualify for social media
            path_parts = file_path.replace("\\", "/").upper().split("/")
            in_publish_subfolder = any("PUBLISH" in part for part in path_parts[:-1])

            if in_publish_subfolder:
                # Quota Check for Daily Broadcasts
                today = datetime.datetime.now().strftime('%Y-%m-%d')
                quota_data = {}
                if os.path.exists(QUOTA_FILE):
                    try:
                        with open(QUOTA_FILE, 'r') as f:
                            quota_data = json.load(f)
                    except: pass
                
                daily_q = quota_data.get(today, {}).get(profile_id, {}).get("total", 0)
                if daily_q >= DAILY_BUFFER_LIMIT:
                    log_msg(f"◈ [QUOTA] Daily limit reached for {channel_id}. Skipping real-time broadcast.")
                    # Standard database synchronization to live feed (is_social=False)
                    insert_pulse_to_supabase(project_name, workflow['label'], asset_url, mood=workflow['mood'], software="Neural Engine", channel_id=channel_id, is_social=False)
                    return

                # Determine Post Type
                post_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
                
                # YouTube Final Check
                if profile_id == BUFFER_PROFILE_ID_BLUE and not is_strict_vertical_video:
                    insert_pulse_to_supabase(project_name, workflow['label'], asset_url, mood=workflow['mood'], software="Neural Engine", channel_id=channel_id, is_social=False)
                    return # Redundant safety

                social_thumb = None
                if is_vid:
                    if not is_vert:
                        formatted = format_video_vertical(file_path)
                        if formatted != file_path:
                            asset_url = upload_to_supabase(formatted, "formatted")
                            os.remove(formatted)
                    social_thumb = generate_and_upload_thumbnail(file_path)

                # Determine CTA based on channel
                cta = ""
                if channel_id == "LANNA":
                    cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more."
                elif channel_id == "BLUE":
                    cta = "\n\nExperience the full spectrum at bluechromatictriangle.com."
                else:
                    cta = "\n\nExplore our world at in-no-v8.com or in-no-v8.world."

                # Creative Title Generation
                creative_project = generate_creative_title(project_name)
                asset_title = generate_creative_title(basename)
                
                # For Memories/Archive, use the asset title prominently
                if "MEMORIES" in path_upper or "ARCHIVE" in path_upper:
                    final_title = asset_title
                else:
                    final_title = f"{creative_project}: {asset_title}"

                msg = f"◈ {channel_id} PULSE ◈\n\n{workflow['label']}: {final_title}.{cta} #StudioPulse #Innov8Labs"
                success = broadcast_to_buffer(msg, profile_id=profile_id, asset_urls=[{"url": asset_url, "thumbnail": social_thumb}] if social_thumb else [asset_url], is_video=is_vid, post_type=post_type, bypass_quota=True)
                
                if success:
                    # Update Quota
                    if today not in quota_data: quota_data[today] = {}
                    if profile_id not in quota_data[today]: quota_data[today][profile_id] = {}
                    quota_data[today][profile_id]["total"] = daily_q + 1
                    with open(QUOTA_FILE, 'w') as f: json.dump(quota_data, f)
                    
                    # Also insert to Supabase for website feed (with is_social=True)
                    insert_pulse_to_supabase(project_name, workflow['label'], asset_url, mood=workflow['mood'], software="Neural Engine", channel_id=channel_id, is_social=True)
                else:
                    # Sync to DB anyway if broadcast failed
                    insert_pulse_to_supabase(project_name, workflow['label'], asset_url, mood=workflow['mood'], software="Neural Engine", channel_id=channel_id, is_social=False)
            else:
                log_msg(f"◈ [HEARTBEAT] Save detected for {basename} ({project_name}) is outside a 'PUBLISH' directory. Bypassing Buffer. Syncing to live portal.")
                # Standard database synchronization to live feed (with is_social=False)
                insert_pulse_to_supabase(project_name, workflow['label'], asset_url, mood=workflow['mood'], software="Neural Engine", channel_id=channel_id, is_social=False)

        except BaseException as e:
            import traceback
            err_msg = traceback.format_exc()
            log_msg(f"◈ [CRITICAL PROCESS ERROR] {type(e).__name__}: {e}\n{err_msg}")

    def dispatch_carousel(self, folder_path):
        """Processes a folder as a single carousel post."""
        try:
            current_week = datetime.datetime.now().strftime('%Y-%U')
            
            # 1. Check Spacing Quota (Every Other Day) and Weekly Limit
            quota_data = {}
            if os.path.exists(QUOTA_FILE):
                try:
                    with open(QUOTA_FILE, 'r') as f:
                        quota_data = json.load(f)
                except: pass

            last_carousel_date_str = quota_data.get("last_lanna_carousel_date")
            can_send = True
            if quota_data.get("weekly_lanna_carousel_sent") == current_week:
                can_send = False
                log_msg(f"◈ [QUOTA] Weekly Lanna Carousel limit already reached for week {current_week}. Moving {os.path.basename(folder_path)} to Pending.")
            elif last_carousel_date_str:
                last_date = datetime.datetime.strptime(last_carousel_date_str, '%Y-%m-%d')
                days_since = (datetime.datetime.now() - last_date).days
                if days_since < 2:
                    can_send = False
                    log_msg(f"◈ [QUOTA] Lanna Carousel spacing not met ({days_since} days since last). Moving {os.path.basename(folder_path)} to Pending.")
            
            if not can_send:
                try:
                    target = os.path.join(PENDING_DIR, "CAROUSELS", os.path.basename(folder_path))
                    if os.path.exists(target): shutil.rmtree(target)
                    shutil.move(folder_path, target)
                except Exception as e: log_msg(f"[QUEUE ERROR] {e}")
                return
            
            # Update last carousel date
            quota_data["last_lanna_carousel_date"] = datetime.datetime.now().strftime('%Y-%m-%d')
            with open(QUOTA_FILE, 'w') as f: json.dump(quota_data, f)
            
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
            creative_title = generate_creative_title(folder_name)
            cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more mystical updates."
            msg = f"◈ LANNA WHISPERS: {creative_title} (Collection) ◈{cta}"
            
            carousel_name = os.path.basename(folder_path)
            creative_label = generate_creative_title(carousel_name)
            action_label = f"◈ LANNA WHISPERS: {creative_label} ◈"
            
            log_msg(f">>> [CAROUSEL] Verified Quota. Dispatching pulse: {action_label}")
            
            # 5. Sync to Website (Unified Pulse)
            # Use the first asset as the cover
            insert_pulse_to_supabase(
                project_name="Lanna Whispers",
                action_label=action_label,
                asset_url=asset_data[0]["url"],
                mood="mystical",
                software="Graphic Engine",
                channel_id="LANNA",
                is_social=True
            )
            
            # 6. Dispatch to Buffer (Respecting Daily Quota)
            broadcast_to_buffer(
                action_label, 
                profile_id=BUFFER_PROFILE_ID_LANNA, 
                asset_urls=asset_data, 
                is_video=has_video, 
                post_type="GRID", 
                bypass_quota=False # Count toward daily limit
            )
            
            # 7. Update Cache & Quota
            try:
                # Update last carousel date
                quota_data["last_lanna_carousel_date"] = datetime.datetime.now().strftime('%Y-%m-%d')
                quota_data["weekly_lanna_carousel_sent"] = current_week
                # Save fingerprint of folder name to prevent re-processing
                cache_key = f"CAROUSEL_{folder_name}"
                last_size_cache[cache_key] = str(time.time())
                
                with open(QUOTA_FILE, 'w') as f: json.dump(quota_data, f)
                save_cache()
            except: pass
            
            # 8. Cleanup Temp Files
            for tf in temp_files:
                try: os.remove(tf)
                except: pass
            
        except Exception as e:
            log_msg(f"[CAROUSEL ERROR] {e}")

            


    def upload_to_supabase_storage(self, file_path):
        """Upload a milestone image to Knownhost FTP."""
        try:
            import ftplib
            FTP_HOST = "ftp.in-no-v8.com"
            FTP_USER = "innov8co"
            FTP_PASS = "%odn*fr*l4a7$e"
            
            filename = f"{int(time.time())}_{os.path.basename(file_path)}"
            
            # Connect to Knownhost FTP
            ftp = ftplib.FTP_TLS(FTP_HOST)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            
            remote_dir = "/in-no-v8.world/vault/studio-assets"
            
            # Ensure remote directory exists
            parts = remote_dir.split('/')
            current = ""
            for part in parts:
                if not part:
                    continue
                current = f"{current}/{part}"
                try:
                    ftp.mkd(current)
                except Exception:
                    pass
                    
            remote_path = f"{remote_dir}/{filename}"
            with open(file_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
                
            ftp.quit()
            
            public_url = f"https://in-no-v8.world/vault/studio-assets/{filename}"
            print(f"Uploaded to Studio Assets FTP: {public_url}")
            return public_url
        except Exception as e:
            print(f"Storage upload FTP error: {e}")
            return None

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
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
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
                filter_complex += f"[v]drawtext=text='INSTRUMENTAL PULSE':font='Arial Black':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2:alpha=0.6:box=1:boxcolor=black@0.4:boxborderw=20[v]"
        else:
            # Green Peak Waveform for Podcasts/Clients
            filter_complex = f"[0:a]showwaves=s=1080x1920:mode=cline:colors=0x00FF00[v];"
            filter_complex += f"[v]drawtext=text='STUDIO AUDIO LOG':font='Arial':fontcolor=0x00FF00:fontsize=36:x=(w-text_w)/2:y=100:alpha=0.8:box=1:boxcolor=black@0.6:boxborderw=20[v]"
        
        cmd = [
            'ffmpeg', '-y', '-ss', str(start), '-t', str(t), '-i', audio_path,
            '-filter_complex', filter_complex,
            '-map', '[v]', '-map', '0:a',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k', output_file
        ]
        
        log_msg(f">>> [RENDER] Executing FFmpeg for Music Visualizer (Duration: {t}s)...")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        
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
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
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
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            
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
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        else:
            log_msg(f">>> [OPTIMIZE] Compressing image: {os.path.basename(file_path)}")
            # Resize to 1920px max, 80% quality
            cmd = [
                'ffmpeg', '-y', '-i', file_path,
                '-vf', "scale='min(1920,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
                '-q:v', '4', # Roughly 80% quality
                output_file
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            
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

        # 2. Check Daily Posts (Fill Today AND Tomorrow)
        posts_pending = sorted([os.path.join(PENDING_DIR, "POSTS", f) for f in os.listdir(os.path.join(PENDING_DIR, "POSTS")) if not f.startswith(".")], key=os.path.getmtime)
        
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        profiles = [BUFFER_PROFILE_ID_LANNA, BUFFER_PROFILE_ID_MAIN, BUFFER_PROFILE_ID_BLUE]
        
        for post_path in posts_pending:
            is_vid = post_path.lower().endswith(('.mp4', '.mov'))
            width, height = get_video_dimensions(post_path)
            is_vert = height > width
            q_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
            
            quota_data = {}
            if os.path.exists(QUOTA_FILE):
                with open(QUOTA_FILE, 'r') as f: quota_data = json.load(f)
            
            # Find a profile that needs this type of content
            released = False
            for p_id in profiles:
                # YouTube (BLUE) ONLY supports REELS
                if p_id == BUFFER_PROFILE_ID_BLUE and q_type != "REEL": continue
                
                # Check today AND tomorrow
                today_count = quota_data.get(today, {}).get(p_id, {}).get(q_type, 0)
                tomorrow_count = quota_data.get(tomorrow, {}).get(p_id, {}).get(q_type, 0)
                
                if today_count < 1 or tomorrow_count < 1:
                    log_msg(f"◈ [BACKLOG] Releasing {q_type} for {p_id} (Target: {today if today_count < 1 else tomorrow}): {os.path.basename(post_path)}")
                    # Move to appropriate live monitoring folder to trigger pulse
                    sub = "LANNA" if p_id == BUFFER_PROFILE_ID_LANNA else "BLUE" if p_id == BUFFER_PROFILE_ID_BLUE else "LABS"
                    dest = os.path.join(WATCH_PATH, "SOCIAL", sub, os.path.basename(post_path))
                    shutil.move(post_path, dest)
                    released = True
                    break
            
            if released: break # Only process one per loop to avoid flooding
        
        # 3. SMART INVENTORY DIAGNOSTIC
        check_inventory_levels()

    except Exception as e:
        log_msg(f"[BACKLOG ERROR] {e}")
    
    # Reschedule Backlog Check every hour (3600 seconds)
    threading.Timer(3600, lambda: process_backlog(handler)).start()

def check_inventory_levels():
    """Performs a specific diagnostic at 9 PM local time and alerts if the buffer is low."""
    global last_inventory_alert_time
    try:
        now_dt = datetime.datetime.now()
        current_date = now_dt.strftime("%Y-%m-%d")
        current_hour = now_dt.hour
        
        # Only fire between 9:00 PM and 9:59 PM
        if current_hour != 21:
            return

        # Check if we've already sent the alert today
        if last_inventory_alert_time == current_date:
            return

        quota_data = {}
        if os.path.exists(QUOTA_FILE):
            try:
                with open(QUOTA_FILE, 'r') as f: quota_data = json.load(f)
            except: pass
        
        daily_quota = quota_data.get(current_date, {})
        
        # Requirements map: {ProfileID: [Required Types]}
        requirements = {
            BUFFER_PROFILE_ID_LANNA: ["STORY", "REEL", "GRID"],
            BUFFER_PROFILE_ID_MAIN: ["STORY", "REEL", "GRID"],
            BUFFER_PROFILE_ID_BLUE: ["REEL"] # YouTube Shorts
        }
        
        missing_reports = []
        
        for profile_id, types in requirements.items():
            channel_label = "LANNA" if profile_id == BUFFER_PROFILE_ID_LANNA else "INN.OV8" if profile_id == BUFFER_PROFILE_ID_MAIN else "BLUE"
            
            for q_type in types:
                queued_today = daily_quota.get(profile_id, {}).get(q_type, 0)
                
                # REDUCED AGGRESSION: Only alert if ZERO posts have been sent today
                # This ensures at least one update happens without daily nagging if target is met.
                if queued_today < 1:
                    # Check if we have anything in PENDING to fill it
                    pending_folder = os.path.join(PENDING_DIR, "POSTS") 
                    pending_count = len([f for f in os.listdir(pending_folder) if not f.startswith('.')])
                    
                    if pending_count == 0:
                        missing_reports.append(f"{channel_label} {q_type}")
        
        if missing_reports:
            log_msg(f"◈ [INVENTORY] Scheduled 9PM Diagnostic: Missing {', '.join(missing_reports)}")
            advice_msg = f"Diagnostic complete. To maintain a 24h buffer, please resupply: {', '.join(missing_reports)}."
            
            
            # Send Email Alert
            send_email_alert(
                subject="◈ STUDIO ALERT: Supply Chain Low",
                message=f"Your 9 PM inventory diagnostic is complete. To maintain your 24-hour buffer for tomorrow, please replenish: <strong>{', '.join(missing_reports)}</strong>."
            )
            
            last_inventory_alert_time = current_date
            save_cache()
        else:
            log_msg("◈ [INVENTORY] 9PM Diagnostic: All queues healthy.")
            last_inventory_alert_time = current_date # Still mark as checked today
            save_cache()
            
    except Exception as e:
        log_msg(f"[INVENTORY DIAGNOSTIC ERROR] {e}")

if __name__ == "__main__":
    import msvcrt
    if not get_lock():
        print(f"Another instance of heartbeat.py is already running. (Lock: {LOCK_PATH})")
        exit(0)
    
    if not URL or not KEY:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
        exit(1)
        
    load_cache()
    log_msg("◈ [STARTUP] Discovery Engine Active. Indexing new activity...")

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
            
            # PROACTIVE STARTUP SCAN: Ingest existing social content
            log_msg("◈ [STARTUP] Scanning for unsent social content...")
            # DYNAMIC DISCOVERY: Scan all top-level folders except ignores (With Fail-Safe)
            social_paths = []
            try:
                top_folders = [d for d in os.listdir(WATCH_PATH) if os.path.isdir(os.path.join(WATCH_PATH, d)) and d not in IGNORE_FOLDERS]
                
                # Prioritize DFP if it exists, otherwise use discovered list
                if "DFP" in top_folders:
                    social_paths.append(os.path.join(WATCH_PATH, "DFP"))
                    top_folders.remove("DFP")
                
                for f in top_folders:
                    social_paths.append(os.path.join(WATCH_PATH, f))
            except Exception as e:
                log_msg(f"◈ [DISCOVERY WARNING] Failed to scan root: {e}. Using fallback paths.")
                social_paths = [os.path.join(WATCH_PATH, "DFP"), os.path.join(WATCH_PATH, "SOCIAL"), os.path.join(WATCH_PATH, "LANNA")]
            
            log_msg(f"◈ [DISCOVERY] Monitoring {len(social_paths)} project root paths.")
            
            processed_folders = set()
            for s_path in social_paths:
                if not os.path.exists(s_path): continue
                for root, dirs, files in os.walk(s_path):
                    if any(ign.lower() in root.lower() for ign in IGNORE_FOLDERS): continue
                    
                    # CAROUSEL DETECTION
                    if "LANNA" in root.upper() and os.path.basename(os.path.dirname(root)).upper() == "LANNA":
                        if root in processed_folders: continue
                        processed_folders.add(root)
                        if files:
                            log_msg(f"◈ [INGEST] Carousel detected: {os.path.basename(root)}")
                            mock_event = type('obj', (object,), {'src_path': os.path.join(root, files[0]), 'is_directory': False})
                            event_handler.process_event(mock_event)
                            continue
                    
                    # SHUFFLE FILES FOR CONTENT VARIETY
                    current_files = list(files)
                    if "MEMORIES" not in root.upper():
                        random.shuffle(current_files)
                    
                    for f in current_files:
                        if any(ign.lower() in f.lower() for ign in IGNORE_FILES): continue
                        ext = os.path.splitext(f)[1].lower().strip()
                        if any(key in ext for key in WORKFLOW_MAP):
                            path = os.path.join(root, f)
                            mock_event = type('obj', (object,), {'src_path': path, 'is_directory': False})
                            event_handler.process_event(mock_event)
                            # Only sleep if it was a real pulse (handled inside process_event now)
                            continue
            
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
