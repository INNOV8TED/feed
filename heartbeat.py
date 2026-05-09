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
        relative = os.relpath(file_path, WATCH_PATH)
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

    url = "https://api.bufferapp.com/1/updates/create.json"
    
    # Payload for the legacy REST API (form-encoded)
    payload = {
        "text": message,
        "profile_ids[]": [BUFFER_PROFILE_ID],
        "access_token": BUFFER_TOKEN,
        "shorten": True
    }
    
    # For form-encoded POST, we don't necessarily need the Authorization header 
    # if the access_token is in the payload, but it doesn't hurt.
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        # Use data= for form-encoding
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            print(f"Successfully broadcasted to Buffer: {message}")
        else:
            print(f"Buffer error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Buffer connection error: {e}")

class HeartbeatHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
            
        file_path = event.src_path
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in WORKFLOW_MAP:
            project_name = get_project_name(file_path)
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
                
                # If milestone, broadcast to social media
                if is_milestone:
                    # Specific message format
                    broadcast_message = f"🚀 New Milestone Reached in #{project_name}! Check the live pulse at feed.in-no-v8.com."
                    broadcast_to_buffer(broadcast_message)
                    
            except Exception as e:
                print(f"Sync error: {e}")

if __name__ == "__main__":
    event_handler = HeartbeatHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()
    print(f"Monitoring {WATCH_PATH} with Buffer integration...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
