import time
import os
import threading
import requests
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
BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")

WATCH_PATH = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK"
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git"]
IGNORE_FILES = ["heartbeat.log", "heartbeat.lock"]
COOLDOWN_SECONDS = 300  # 5-minute cooldown for the same project/activity
DEBOUNCE_SECONDS = 2.0  # 2-second debounce for rapid file changes

# Global cache to persist across observer restarts
last_sent_cache = {}
pending_timers = {}

# --- SINGLETON LOCK ---
LOCK_FILE = "heartbeat.lock"
try:
    if os.path.exists(LOCK_FILE):
        # Check if the process is actually running (simple file existence for now, but we'll try to remove it on exit)
        os.remove(LOCK_FILE)
    
    # Create the lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
        
    import atexit
    def cleanup():
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    atexit.register(cleanup)
except Exception as e:
    print(f"Singleton check failed: {e}. If this is a duplicate process, it will exit.")

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
    try:
        relative = os.path.relpath(file_path, WATCH_PATH)
    except ValueError:
        return None
        
    parts = relative.split(os.sep)
    if len(parts) > 1:
        project = parts[0]
        if project in IGNORE_FOLDERS:
            return None
        return project
    return "General Workspace"

def broadcast_to_buffer(message):
    if not BUFFER_TOKEN or not BUFFER_PROFILE_ID or "your_buffer" in BUFFER_TOKEN:
        print("Buffer credentials not configured. Skipping broadcast.")
        return

    url = "https://api.buffer.com"
    
    # GraphQL mutation for creating a post with assets
    mutation = """
    mutation CreateNewPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id text }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    
    # Use a guaranteed 1080x1080 image for this test (Lorem Picsum)
    test_image_url = "https://picsum.photos/1080/1080"
    
    variables = {
        "input": {
            "text": message,
            "channelId": BUFFER_PROFILE_ID,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": {
                "images": [{"url": test_image_url}]
            },
            "metadata": {
                "instagram": {
                    "type": "post",
                    "shouldShareToFeed": True
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
                # Use ascii for error messages to be safe
                safe_err = str(data['errors']).encode('ascii', 'ignore').decode('ascii')
                print(f"Buffer GraphQL Error: {safe_err}")
            else:
                try:
                    post_id = data['data']['createPost']['post']['id']
                    print(f"Success! Post created with ID: {post_id}")
                except:
                    print(f"Buffer Response Data: {data}")
        else:
            safe_body = response.text.encode('ascii', 'ignore').decode('ascii')
            print(f"Buffer HTTP error: {response.status_code} - {safe_body}")
    except Exception as e:
        print("Buffer broadcast script error (likely console encoding related). Check Buffer UI.")

class HeartbeatHandler(FileSystemEventHandler):
    def on_modified(self, event):
        self.process_event(event)
        
    def on_created(self, event):
        self.process_event(event)

    def process_event(self, event):
        if event.is_directory:
            return
            
        file_path = event.src_path
        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        if filename in IGNORE_FILES:
            return
            
        # DEBUG LOGGING
        with open("heartbeat.log", "a") as f:
            f.write(f"[{time.ctime()}] Event: {event.event_type} | Path: {file_path}\n")

        if ext in WORKFLOW_MAP:
            project_name = get_project_name(file_path)
            
            if project_name == "PUBLISH":
                project_name = "General Workspace"

            if not project_name:
                return
                
            workflow = WORKFLOW_MAP[ext]
            
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
        
        # DEBOUNCE & COOLDOWN (Tuned for responsiveness)
        cooldown_key = f"{project_name}_{workflow['label']}"
        current_time = time.time()
        if cooldown_key in last_sent_cache:
            if current_time - last_sent_cache[cooldown_key] < 30: # 30s cooldown
                return
        
        last_sent_cache[cooldown_key] = current_time
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # SOFTWARE DETECTION
        software_map = {
            ".prproj": "Premiere Pro",
            ".psd": "Photoshop",
            ".aep": "After Effects",
            ".wav": "Ableton Live",
            ".mp4": "Media Encoder",
            ".mov": "DaVinci Resolve",
            ".png": "Graphic Engine",
            ".jpg": "Graphic Engine"
        }
        software = software_map.get(ext, "Creative Engine")

        # CAPTURE RECENT ASSET
        asset_url = None
        try:
            parent_dir = os.path.dirname(file_path)
            images = [os.path.join(parent_dir, f) for f in os.listdir(parent_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
            if images:
                latest_image = max(images, key=os.path.getmtime)
                # Upload to Supabase Storage
                with open(latest_image, 'rb') as f:
                    file_ext = os.path.splitext(latest_image)[1]
                    storage_path = f"pulses/{int(time.time())}{file_ext}"
                    supabase.storage.from_('studio-assets').upload(storage_path, f.read())
                    asset_url = supabase.storage.from_('studio-assets').get_public_url(storage_path)
        except Exception as e:
            print(f"Asset capture failed: {e}")

        # GENERATE NARRATIVE
        mood = workflow['mood']
        narratives = {
            "focused": ["Neural link stable. Processing assets...", "Deep in the flow state.", "Optimizing production pipeline."],
            "creative": ["Synthesizing new realities.", "Exploring visual frontiers.", "Hacking the aesthetic."],
            "artistic": ["Refining the master stroke.", "Color grade finalized.", "Artistic vision manifesting."],
            "success": ["Milestone reached. Export complete.", "Finalizing delivery.", "Project output successful."],
            "musical": ["Harmonizing frequencies.", "Synthesizer link established.", "Audio pipeline clear."]
        }
        sub_label = narratives.get(mood, ["Active in the studio."])[int(time.time()) % 3]

        data = {
            "project_name": project_name,
            "action_label": workflow["label"],
            "mood_tag": f"{mood}|{sub_label}|{asset_url or ''}|{software}", # Pack software too
            "source": "Windows-Workstation",
            "is_milestone": (ext == ".mp4")
        }
        
        try:
            supabase.table("studio_heartbeat").insert(data).execute()
            print(f"◈ Pulse Sent: {project_name} | {workflow['label']} | via {software}")
            
            # If milestone, broadcast to Buffer
            if data["is_milestone"]:
                msg = f"🚀 New Milestone Reached in #{project_name}! Check the live pulse at feed.in-no-v8.com."
                broadcast_to_buffer(msg)
                
        except Exception as e:
            print(f"Sync error: {e}")

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

if __name__ == "__main__":
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
