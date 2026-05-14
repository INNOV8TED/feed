
import os
import sys
import time
import json
import traceback

# Add the activity_feed directory to the path so we can import heartbeat
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from heartbeat import insert_pulse_to_supabase, upload_to_supabase, get_project_name, WORKFLOW_MAP, log_msg

WATCH_PATH = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK"
FILE_PATH = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\DFP\TLFOP\E362\DELIVERABLES\TLFOP - E362.mp4"

def force_pulse():
    print(f"[FORCE PULSE] Target: {FILE_PATH}")
    
    if not os.path.exists(FILE_PATH):
        print(f"!!! Error: File not found: {FILE_PATH}")
        return

    try:
        project_name = get_project_name(FILE_PATH)
        action_label = f"[{project_name}] Final Deliverable Pulse"
        
        print(f">>> Uploading to Supabase...")
        asset_url = upload_to_supabase(FILE_PATH)
        
        if not asset_url:
            print("!!! Error: Upload failed.")
            return
            
        print(f">>> Success! Asset URL: {asset_url}")
        print(f">>> Inserting Pulse to Website Feed...")
        
        res = insert_pulse_to_supabase(
            project_name=project_name,
            action_label=action_label,
            asset_url=asset_url,
            mood="accomplished",
            software="Video Engine",
            quote="Great things are done by a series of small things brought together. - Van Gogh",
            channel_id="INNOV8",
            is_milestone=True,
            is_social=False
        )
        
        print(f"[COMPLETE] Pulse verified: {res}")
        
    except Exception as e:
        print(f"!!! CRASH: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    force_pulse()
