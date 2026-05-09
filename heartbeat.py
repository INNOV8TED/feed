import time
import os
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
        if event.is_directory:
            return
            
        file_path = event.src_path
        # print(f"File modified: {file_path}") # DEBUG PRINT
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in WORKFLOW_MAP:
            project_name = get_project_name(file_path)
            
            # If project_name is 'PUBLISH', try to find a better name from the path
            if project_name == "PUBLISH":
                # This happens if you save directly to ACTIVE_WORK/PUBLISH
                project_name = "General Workspace"

            if not project_name:
                return
                
            workflow = WORKFLOW_MAP[ext]
            
            # CRITICAL TRIGGER: Trigger only when file is in a folder named 'PUBLISH'
            # We check if 'PUBLISH' is one of the folder names in the path
            path_parts = file_path.upper().split(os.sep)
            is_milestone = "PUBLISH" in path_parts
            
            print(f"Activity: {project_name} ({workflow['label']})")
            
            data = {
                "project_name": project_name,
                "action_label": workflow["label"],
                "mood_tag": workflow["mood"],
                "source": "Windows-Workstation",
                "is_milestone": is_milestone
            }
            
            try:
                # Sync to Supabase
                supabase.table("studio_heartbeat").insert(data).execute()
                
                # If milestone, check if it's an image and upload to storage
                if is_milestone and any(file_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png']):
                    self.upload_to_supabase_storage(file_path)
                    
            except Exception as e:
                print(f"Sync error: {e}")

    def upload_to_supabase_storage(self, file_path):
        """Upload a milestone image to Supabase Storage."""
        filename = os.path.basename(file_path)
        # Create a unique path in the bucket using the timestamp
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
            print(f"Monitoring {WATCH_PATH} with Buffer integration (Self-Healing Active)...")
            
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
