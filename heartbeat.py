import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from supabase import create_client

# --- CONFIGURATION ---
URL = "https://dzgyqrnmsnhqaiqthzok.supabase.co"
KEY = "sb_publishable_TZOHRPfCaaV1AyIVErNknw_IzEsmhtQ"
WATCH_PATH = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK"
IGNORE_FOLDERS = ["activity_feed", "node_modules", ".git"]

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
    # Calculate the relative path from the root
    try:
        relative = os.relpath(file_path, WATCH_PATH)
    except ValueError:
        return None
        
    # The first part of the path is the project subfolder
    parts = relative.split(os.sep)
    
    if len(parts) > 1:
        project = parts[0]
        # Skip if the project is in our ignore list
        if project in IGNORE_FOLDERS:
            return None
        return project
    
    # If it's a file directly in ACTIVE_WORK, it's "General Workspace"
    return "General Workspace"

class HeartbeatHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Ignore directories
        if event.is_directory:
            return
            
        ext = os.path.splitext(event.src_path)[1].lower()
        
        if ext in WORKFLOW_MAP:
            # Extract top-level folder name as Project Name
            project_name = get_project_name(event.src_path)
            
            # If it returns None, it means the file is in an ignored folder
            if not project_name:
                return
                
            workflow = WORKFLOW_MAP[ext]
            
            print(f"Activity: {project_name} ({workflow['label']})")
            
            data = {
                "project_name": project_name,
                "action_label": workflow["label"],
                "mood_tag": workflow["mood"],
                "source": "Windows-Workstation"
            }
            
            try:
                supabase.table("studio_heartbeat").insert(data).execute()
            except Exception as e:
                print(f"Sync error: {e}")

if __name__ == "__main__":
    event_handler = HeartbeatHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()
    print(f"Monitoring {WATCH_PATH}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
