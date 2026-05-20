import os
import sys
import msvcrt

# Force stdout/stderr to use UTF-8 and handle encoding errors gracefully
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')

# Set working directory to the script's directory to ensure relative paths resolve correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Singleton Lock Guard to prevent duplicate processes
LOCK_PATH = "ai_vision_sifter.lock"
lock_file_handle = None

def get_lock():
    global lock_file_handle
    try:
        lock_file_handle = open(LOCK_PATH, "w")
        msvcrt.locking(lock_file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file_handle.write(str(os.getpid()))
        lock_file_handle.flush()
        return True
    except Exception:
        return False

if not get_lock():
    print("Another instance of ai_vision_sifter is already running. Exiting.")
    sys.exit(0)

import json
import zipfile
import io
import requests
import base64
from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()
from dotenv import load_dotenv
from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from gcp_gemini_client import call_gemini
from tqdm import tqdm
import time
import datetime

load_dotenv()

import cv2

def process_video_node(video_bytes, filename):
    """
    Processes a raw video node by saving it to a temp file, then:
    1. Extracts a middle frame (PIL Image) for Supabase static preview and AI sifting.
    2. Generates a 10-second preview clip using FFmpeg.
    3. Detects video dimensions (width, height) to classify as Vertical or Horizontal.
    4. Automatically exports the 10-second clip to the SOCIAL folder in the correct subfolder (REELS_STORIES or POSTS).
    5. Returns (PIL Image, temp_preview_path, is_vertical).
    """
    temp_video_path = './temp_video_extract.mp4'
    temp_preview_path = './temp_video_preview.mp4'
    
    img = None
    success_frame = False
    is_vertical = False
    
    try:
        # Write video bytes to temp file
        with open(temp_video_path, 'wb') as f:
            f.write(video_bytes)
            
        # 1. Grab middle frame using OpenCV
        cap = cv2.VideoCapture(temp_video_path)
        success_frame, frame = cap.read()
        
        width = 1920
        height = 1080
        total_frames = 0
        fps = 30.0
        
        if success_frame:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            
            # Grab frame 30 (approx 1s in) or the middle frame to bypass black entry frames
            target_frame = min(30, total_frames // 2) if total_frames > 0 else 0
            if target_frame > 0:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                success_target, target_img = cap.read()
                if success_target:
                    frame = target_img
                    
        cap.release()
        
        if success_frame and frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
        # 2. Check orientation
        is_vertical = height > width
        
        # 3. Generate 10-second preview clip using FFmpeg
        import subprocess
        duration = 10.0
        if total_frames > 0 and fps > 0:
            duration = total_frames / fps
            
        start_time = 2.0 if duration > 12.0 else 0.0
        clip_duration = min(10.0, duration)
        
        # Optimize transcoding to produce extremely small, high-quality previews
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(clip_duration), '-i', temp_video_path,
            '-vf', 'scale=-2:480',
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '36',
            '-movflags', '+faststart',
            '-an', temp_preview_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        
        # 4. Export to SOCIAL directory if path exists
        social_dir = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL"
        if os.path.exists(social_dir):
            memories_dir = os.path.join(social_dir, "INNOV8", "MEMORIES")
            subfolder = "REELS_STORIES" if is_vertical else "POSTS"
            target_export_dir = os.path.join(memories_dir, subfolder)
            
            if not os.path.exists(target_export_dir):
                os.makedirs(target_export_dir)
                
            clean_filename = filename.replace(" ", "_")
            prefix = "REEL_STORY_" if is_vertical else "POST_"
            export_path = os.path.join(target_export_dir, f"{prefix}{clean_filename}")
            
            import shutil
            shutil.copy2(temp_preview_path, export_path)
            print(f"\n[SOCIAL EXPORT] Exported 10s {prefix.strip('_')} preview to: {export_path}")
            
    except Exception as e:
        print(f"Error in process_video_node: {e}")
    finally:
        try:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
        except:
            pass
            
    return img, temp_preview_path, is_vertical

# --- Config & Setup ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
SCOPES = ['https://www.googleapis.com/auth/drive']
current_token = ""

def refresh_token_now():
    global current_token
    creds = Credentials.from_authorized_user_file('token_drive.json', SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open('token_drive.json', 'w') as token_f:
                token_f.write(creds.to_json())
    current_token = creds.token

class TeleportingStream(io.RawIOBase):
    def __init__(self, file_id, total_size, token, session):
        self.file_id = file_id
        self.total_size = total_size
        self.token = token
        self.session = session
        self.url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        self.pos = 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET: self.pos = offset
        elif whence == io.SEEK_CUR: self.pos += offset
        elif whence == io.SEEK_END: self.pos = self.total_size + offset
        return self.pos

    def readinto(self, b):
        size = len(b)
        if self.pos >= self.total_size: return 0
        end = min(self.pos + size - 1, self.total_size - 1)
        headers = {'Authorization': f'Bearer {self.token}', 'Range': f'bytes={self.pos}-{end}'}
        r = self.session.get(self.url, headers=headers, timeout=180)
        if r.status_code == 401:
            refresh_token_now()
            self.token = current_token
            return self.readinto(b)
        data = r.content
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)

def analyze_image_with_gemini(base64_img):
    prompt = """
    You are the INNOV8 Studio Archive Curator. 
    Your job is to strictly filter, score, and tag photos for a public cinematic map interface.
    
    RULES:
    1. REJECT any blurry, accidental, pocket-dials, screenshots, or private domestic photos.
    2. EXCEPTION: Street photography featuring the backs of people (where faces are obscured) is a deliberate artistic series and must be ACCEPTED and tagged 'STREET_SERIES'.
    3. EXCEPTION: Explicit historical travel, childhood, and personal archive photos specifically requested by the user must be ACCEPTED, scored, and tagged as 'HISTORICAL_ARCHIVE', 'TRAVEL_SCOUTING', or 'CHILDHOOD_MEMORIES'.
    4. Categorize accepted photos using exactly 2 stark, terminal-style tags (e.g. 'URBAN_SCOUTING', 'ARCHITECTURAL', 'STUDIO_NODE', 'CINEMATIC').
    
    Respond ONLY with a valid JSON object matching this exact structure:
    {
        "score": 8,
        "reject": false,
        "reject_reason": "",
        "tags": ["TAG_1", "TAG_2"]
    }
    """
    
    try:
        response_text = call_gemini(
            prompt="Analyze this image according to your instructions and return the JSON object.",
            system_instruction=prompt,
            image_data=base64_img,
            response_json=True
        )
        if response_text:
            result = json.loads(response_text)
            # Add a mock usage dict so the cost calculation doesn't fail
            result['usage'] = {"prompt_tokens": 0, "completion_tokens": 0}
            return result
        else:
            return {"reject": True, "reject_reason": "API_ERROR", "usage": {}}
    except Exception as e:
        print(f"[SIFTER] Gemini API Error: {e}")
        return {"reject": True, "reject_reason": "API_ERROR", "usage": {}}

def is_duplicate_time_location(node, inventory, time_tol_seconds=120, coord_tol_degrees=0.0001):
    node_coords = node.get('coords')
    node_ts_str = node.get('timestamp')
    if not node_coords or len(node_coords) < 2 or not node_ts_str:
        return False
        
    try:
        node_ts = float(node_ts_str)
    except:
        return False
        
    node_lat, node_lon = node_coords[0], node_coords[1]
    if abs(node_lat) < 0.001 and abs(node_lon) < 0.001:
        return False

    for other in inventory:
        if other is node:
            continue
            
        other_tags = other.get('vision_tags')
        is_processed_accepted = (
            'thumb_url' in other or 
            (other_tags and "ERROR" not in other_tags and "AI_REJECTED" not in other_tags)
        )
        if not is_processed_accepted:
            continue
            
        other_coords = other.get('coords')
        other_ts_str = other.get('timestamp')
        if not other_coords or len(other_coords) < 2 or not other_ts_str:
            continue
            
        try:
            other_ts = float(other_ts_str)
        except:
            continue
            
        other_lat, other_lon = other_coords[0], other_coords[1]
        
        if abs(node_ts - other_ts) <= time_tol_seconds:
            dist = ((node_lat - other_lat)**2 + (node_lon - other_lon)**2)**0.5
            if dist <= coord_tol_degrees:
                return True
                
    return False

_shared_ftp = None
_created_dirs = set()

def get_ftp_connection():
    global _shared_ftp
    if _shared_ftp is not None:
        return _shared_ftp
            
    import ftplib
    FTP_HOST = "ftp.in-no-v8.com"
    FTP_USER = "innov8co"
    FTP_PASS = "%odn*fr*l4a7$e"
    
    ftp = ftplib.FTP_TLS(FTP_HOST, timeout=15)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()
    _shared_ftp = ftp
    return ftp

def upload_to_ftp(data_or_path, filename, folder="vault-images"):
    try:
        ftp = get_ftp_connection()
        remote_dir = f"/in-no-v8.world/vault/{folder}"
        
        # Ensure remote directory exists (only once per folder)
        global _created_dirs
        if remote_dir not in _created_dirs:
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
            _created_dirs.add(remote_dir)
                
        remote_path = f"{remote_dir}/{filename}"
        
        if isinstance(data_or_path, bytes):
            bio = io.BytesIO(data_or_path)
            ftp.storbinary(f'STOR {remote_path}', bio)
        else:
            with open(data_or_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_path}', f)
                
        return f"https://in-no-v8.world/vault/{folder}/{filename}"
    except Exception as e:
        print(f"FTP Upload Error: {e}")
        global _shared_ftp
        _shared_ftp = None
        return None

def run_sifter(batch_size=100):
    print("--- INNOV8 AI VISION SIFTER ---")
    refresh_token_now()
    
    if not os.path.exists('vault_inventory.json'):
        print("Error: vault_inventory.json not found.")
        return

    with open('vault_inventory.json', 'r', encoding='utf-8') as f:
        inventory = json.load(f)
        
    print(f"Loaded {len(inventory)} total nodes.")
    
    # Filter for unprocessed images/videos (skipping errors to avoid infinite loops), supporting images and videos (.mp4, .mov)
    unprocessed = [n for n in inventory if 'vision_tags' not in n]
    
    if not unprocessed:
        print("No unprocessed nodes found! You're all caught up.")
        return
        
    test_batch = unprocessed[:batch_size]
    print(f"Processing test batch of {len(test_batch)} nodes...\n")
    
    master_session = requests.Session()
    
    # Initialize global counts instead of session counts
    total_valid_nodes = len(inventory)
    initial_processed_count = total_valid_nodes - len(unprocessed)
    processed_count = initial_processed_count
    accepted_count = sum(1 for n in inventory if 'thumb_url' in n)
    rejected_count = sum(1 for n in inventory if n.get('vision_tags') == ["AI_REJECTED"])
    
    start_time = time.time()
    supabase_bytes = 0
    openai_cost_usd = 0.0
    
    if os.path.exists('sifter_status.json'):
        try:
            with open('sifter_status.json', 'r') as sf:
                st = json.load(sf)
                supabase_bytes = st.get('supabase_bytes', 0)
                openai_cost_usd = st.get('openai_cost_usd', 0.0)
        except: pass
    
    # Group nodes by zip_id to avoid downloading the massive ZIP central directory over HTTP repeatedly
    from collections import defaultdict
    nodes_by_zip = defaultdict(list)
    for node in test_batch:
        nodes_by_zip[node['zip_id']].append(node)
        
    # Create a progress bar
    pbar = tqdm(total=len(test_batch), desc="Sifting Archives", unit="img")
    
    for zip_id, nodes in nodes_by_zip.items():
        try:
            zip_size = nodes[0]['zip_size']
            # If the ZIP is small (under 100MB), download it directly to RAM to bypass HTTP range bottlenecks
            if zip_size < 100 * 1024 * 1024:
                pbar.write(f"Downloading small archive entirely to RAM ({zip_size / (1024*1024):.2f} MB)...")
                url = f"https://www.googleapis.com/drive/v3/files/{zip_id}?alt=media"
                headers = {'Authorization': f'Bearer {current_token}'}
                r = master_session.get(url, headers=headers)
                if r.status_code == 401:
                    refresh_token_now()
                    headers = {'Authorization': f'Bearer {current_token}'}
                    r = master_session.get(url, headers=headers)
                stream = io.BytesIO(r.content)
            else:
                # Teleporting Stream directly from Google Drive API for large files
                stream = TeleportingStream(zip_id, zip_size, current_token, master_session)
            
            with zipfile.ZipFile(stream, 'r') as zf:
                for node in nodes:
                    temp_preview_path = None
                    try:
                        image_path = node['image_path']
                        filename = os.path.basename(image_path)
                        
                        # Check duplicate
                        if is_duplicate_time_location(node, inventory):
                            node['vision_tags'] = ["AI_REJECTED"]
                            node['reject_reason'] = "DUPLICATE_TIME_LOCATION"
                            rejected_count += 1
                            pbar.write(f"Skipping duplicate: {filename} (same location & time)")
                            continue
                        
                        # Check video
                        ext = image_path.split('.')[-1].lower()
                        is_video = ext in ['mp4', 'mov', '3gp']
                        
                        if is_video:
                            pbar.write(f"Processing and transcoding video node: {filename}")
                            try:
                                # 1. Extract video bytes
                                with zf.open(image_path) as video_file:
                                    video_bytes = video_file.read()
                                
                                # 2. Call our built-in video processor
                                img, temp_preview, is_vertical = process_video_node(video_bytes, filename)
                                
                                if img:
                                    # Convert frame to WebP bytes for high-fidelity custom thumbnail
                                    webp_io = io.BytesIO()
                                    img.save(webp_io, format="WEBP", quality=80)
                                    webp_bytes = webp_io.getvalue()
                                    
                                    storage_path = f"{filename.split('.')[0]}.webp"
                                    thumb_url = upload_to_ftp(webp_bytes, storage_path, "vault-images")
                                    node['thumb_url'] = thumb_url
                                else:
                                    node['thumb_url'] = "mp4_placeholder.jpg"
                                    
                                if temp_preview and os.path.exists(temp_preview):
                                    # Upload 10s silent looping preview clip to FTP vault-videos
                                    base_name = filename.rsplit('.', 1)[0]
                                    target_filename = f"{base_name}.mp4"
                                    video_url = upload_to_ftp(temp_preview, target_filename, folder="vault-videos")
                                    node['video_preview_url'] = video_url
                                    pbar.write(f"  [LIVE VIDEO] Hosted: {video_url}")
                                    
                            except Exception as video_err:
                                pbar.write(f"  [WARNING] Video processing bypassed: {video_err}")
                                node['thumb_url'] = "mp4_placeholder.jpg"
                            finally:
                                # Cleanup sifter temporary files
                                for p in ['./temp_video_extract.mp4', './temp_video_preview.mp4']:
                                    if os.path.exists(p):
                                        try: os.remove(p)
                                        except: pass
                                        
                            node['vision_tags'] = ["VIDEO", "CINEMATIC"]
                            processed_count += 1
                            accepted_count += 1
                            
                            # Keep progress status file updated
                            session_processed = processed_count - initial_processed_count
                            elapsed = time.time() - start_time
                            avg_time = elapsed / session_processed if session_processed > 0 else 0
                            remaining = total_valid_nodes - processed_count
                            eta_seconds = remaining * avg_time
                            
                            status_data = {
                                "status": "RUNNING",
                                "last_update": datetime.datetime.now().isoformat(),
                                "total_target": total_valid_nodes,
                                "processed_count": processed_count,
                                "accepted_count": accepted_count,
                                "rejected_count": rejected_count,
                                "supabase_bytes": supabase_bytes,
                                "openai_cost_usd": openai_cost_usd,
                                "eta_seconds": eta_seconds
                            }
                            try:
                                with open('sifter_status.json', 'w') as sf:
                                    json.dump(status_data, sf)
                            except: pass
                            
                            if processed_count % 10 == 0:
                                clean_inventory = [n for n in inventory if n.get('vision_tags') != ["AI_REJECTED"]]
                                tmp_path = 'vault_inventory.json.tmp'
                                with open(tmp_path, 'w', encoding='utf-8') as f:
                                    json.dump(clean_inventory, f)
                                os.replace(tmp_path, 'vault_inventory.json')
                            
                            pbar.update(1)
                            continue
                            
                        # 2. Extract specific media entirely into RAM
                        with zf.open(image_path) as img_file:
                            img_bytes = img_file.read()
                            
                        # 3. Handle image vs video frame extraction & compress to WebP
                        ext = image_path.split('.')[-1].lower()
                        is_video = ext in ['mp4', 'mov', '3gp']
                        
                        temp_preview_path = None
                        is_vertical = False
                        
                        if is_video:
                            img, temp_preview_path, is_vertical = process_video_node(img_bytes, filename)
                            if img is None:
                                pbar.write(f"Failed to extract frame from video: {filename}")
                                node['vision_tags'] = ["ERROR"]
                                continue
                        else:
                            img = Image.open(io.BytesIO(img_bytes))
                            try:
                                from PIL import ImageOps
                                img = ImageOps.exif_transpose(img)
                            except Exception as exif_err:
                                pbar.write(f"EXIF transpose failed: {exif_err}")
                            
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        img.thumbnail((768, 768), Image.Resampling.LANCZOS)
                        
                        webp_buffer = io.BytesIO()
                        img.save(webp_buffer, format="WEBP", quality=60)
                        webp_bytes = webp_buffer.getvalue()
                        
                        # Memory cleanup
                        del img
                        del img_bytes
                        
                        # 4. OpenAI Vision Analysis
                        is_historical_archive = (
                            "fall04_nanjing" in image_path.lower() or
                            "dsci0006" in image_path.lower() or
                            node.get('zip_id') in ["11Rqx3WEEqO3IsDUGysqdl8WKDAhuFnRk", "1qxN31sWsmeBCuKEXcPve6iZZOC-Zs9C4"]
                        )
                        
                        if is_historical_archive:
                            pbar.write(f"  [HISTORICAL BYPASS] Force-accepting requested archive: {filename}")
                            ai_result = {
                                "reject": False,
                                "score": 9,
                                "tags": ["HISTORICAL_ARCHIVE", "TRAVEL_SCOUTING"],
                                "usage": {"prompt_tokens": 0, "completion_tokens": 0}
                            }
                        else:
                            base64_str = base64.b64encode(webp_bytes).decode('utf-8')
                            ai_result = analyze_image_with_gemini(base64_str)
                        
                        usage = ai_result.get('usage', {})
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        cost = (prompt_tokens * 5.0 / 1000000.0) + (completion_tokens * 15.0 / 1000000.0)
                        openai_cost_usd += cost
                        
                        if ai_result.get('reject'):
                            # Flag for deletion
                            node['vision_tags'] = ["AI_REJECTED"]
                            node['reject_reason'] = ai_result.get('reject_reason', 'Unknown')
                            rejected_count += 1
                        else:
                            # 5. Upload to Hostgator FTP
                            storage_path = f"{node['timestamp']}_{filename.split('.')[0]}.webp"
                            
                            try:
                                public_url = upload_to_ftp(webp_bytes, storage_path, "vault-images")
                                if public_url:
                                    node['thumb_url'] = public_url
                                    supabase_bytes += len(webp_bytes)
                                else:
                                    raise Exception("FTP upload returned None")
                            except Exception as upload_err:
                                pbar.write(f"FTP Upload failed for WebP: {upload_err}")
                                node['vision_tags'] = ["ERROR"]
                                continue
                            
                            # Upload 10-second video preview if generated
                            if is_video and temp_preview_path and os.path.exists(temp_preview_path):
                                storage_path_mp4 = f"{node['timestamp']}_{filename.split('.')[0]}.mp4"
                                try:
                                    public_url_mp4 = upload_to_ftp(temp_preview_path, storage_path_mp4, "vault-images")
                                    if public_url_mp4:
                                        node['video_preview_url'] = public_url_mp4
                                        # Track size locally to keep telemetry working
                                        with open(temp_preview_path, 'rb') as mp4_f:
                                            supabase_bytes += len(mp4_f.read())
                                    else:
                                        pbar.write(f"Warning: FTP preview upload failed")
                                except Exception as upload_err:
                                    pbar.write(f"Warning: FTP preview upload failed: {upload_err}")
                            
                            raw_tags = ai_result.get('tags', ["VERIFIED"])
                            if is_video:
                                node['vision_tags'] = ["VIDEO"] + [t for t in raw_tags if t != "VIDEO"]
                            else:
                                node['vision_tags'] = raw_tags
                            node['aesthetic_score'] = ai_result.get('score', 0)
                            accepted_count += 1
                            
                    except Exception as e:
                        pbar.write(f"\nError processing node {node.get('image_path')}: {e}")
                        node['vision_tags'] = ["ERROR"]
                        
                    finally:
                        if temp_preview_path and os.path.exists(temp_preview_path):
                            try:
                                os.remove(temp_preview_path)
                            except:
                                pass
                        processed_count += 1
                        pbar.update(1)
                        
                        session_processed = processed_count - initial_processed_count
                        elapsed = time.time() - start_time
                        avg_time = elapsed / session_processed if session_processed > 0 else 0
                        remaining = total_valid_nodes - processed_count
                        eta_seconds = remaining * avg_time
                        
                        status_data = {
                            "status": "RUNNING",
                            "last_update": datetime.datetime.now().isoformat(),
                            "total_target": total_valid_nodes,
                            "processed_count": processed_count,
                            "accepted_count": accepted_count,
                            "rejected_count": rejected_count,
                            "supabase_bytes": supabase_bytes,
                            "openai_cost_usd": openai_cost_usd,
                            "eta_seconds": eta_seconds
                        }
                        try:
                            with open('sifter_status.json', 'w') as sf:
                                json.dump(status_data, sf)
                        except: pass
                        
                        if processed_count % 10 == 0:
                            clean_inventory = [n for n in inventory if n.get('vision_tags') != ["AI_REJECTED"]]
                            tmp_path = 'vault_inventory.json.tmp'
                            with open(tmp_path, 'w', encoding='utf-8') as f:
                                json.dump(clean_inventory, f)
                            os.replace(tmp_path, 'vault_inventory.json')
                        
                        time.sleep(0.5)
                        
        except Exception as outer_e:
            pbar.write(f"\nCritical Error with ZIP {zip_id}: {outer_e}")
            
    pbar.close()
    
    # Final save and cull
    clean_inventory = [n for n in inventory if n.get('vision_tags') != ["AI_REJECTED"]]
    tmp_path = 'vault_inventory.json.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(clean_inventory, f)
    os.replace(tmp_path, 'vault_inventory.json')
        
    if os.path.exists('sifter_status.json'):
        try:
            with open('sifter_status.json', 'r') as sf:
                st = json.load(sf)
            
            # Recalculate remaining unprocessed nodes to determine correct status
            with open('vault_inventory.json', 'r', encoding='utf-8') as f:
                inv = json.load(f)

            still_unprocessed = [n for n in inv if 'vision_tags' not in n]
            
            if not still_unprocessed:
                st['status'] = "COMPLETE"
            else:
                st['status'] = "PAUSED"
                
            st['last_update'] = datetime.datetime.now().isoformat()
            with open('sifter_status.json', 'w') as sf:
                json.dump(st, sf)
        except:
            pass
            
    # Close persistent FTP connection
    global _shared_ftp
    if _shared_ftp is not None:
        try:
            _shared_ftp.quit()
        except:
            pass
        _shared_ftp = None
        
    print(f"\n--- BATCH COMPLETE ---")
    print(f"Processed: {processed_count}")
    print(f"Accepted & Uploaded: {accepted_count}")
    print(f"Rejected & Culled: {rejected_count}")
    print(f"Final Inventory Size: {len(clean_inventory)} nodes")

if __name__ == "__main__":
    print("AI Vision Sifter Daemon Initialized.")
    while True:
        try:
            if not os.path.exists('vault_inventory.json'):
                print("Error: vault_inventory.json not found. Retrying in 10 seconds...")
                time.sleep(10)
                continue
                
            with open('vault_inventory.json', 'r', encoding='utf-8') as f:
                inv = json.load(f)
                
            still_unprocessed = [n for n in inv if 'vision_tags' not in n]
            
            if not still_unprocessed:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sifter Daemon: All {len(inv)} nodes are fully sifted! Catching up in 5 minutes...")
                # Ensure telemetry matches COMPLETE state
                if os.path.exists('sifter_status.json'):
                    try:
                        with open('sifter_status.json', 'r') as sf:
                            st = json.load(sf)
                        st['status'] = "COMPLETE"
                        st['last_update'] = datetime.datetime.now().isoformat()
                        with open('sifter_status.json', 'w') as sf:
                            json.dump(st, sf)
                    except: pass
                time.sleep(300)
                continue
                
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Sifter Daemon: Found {len(still_unprocessed)} unprocessed nodes. Starting high-frequency batch of 100 targets...")
            
            # Run a batch of 100 to maintain maximum system stability and keep telemetry fresh
            run_sifter(batch_size=100)
            
            # Deploy minified database to remote server automatically
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sifter Daemon: Deploying updated minified database to live server...")
            try:
                import subprocess
                subprocess.run(['python', 'ftp_deploy.py'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sifter Daemon: Live deployment complete!")
            except Exception as deploy_err:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sifter Daemon: Warning, automatic batch deploy failed: {deploy_err}")
            
            # Short rest between batches to prevent API rate limit fatigue
            time.sleep(5)
            
        except Exception as daemon_err:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Critical Daemon Loop Error: {daemon_err}")
            print("Auto-recovering and retrying in 15 seconds...")
            time.sleep(15)
