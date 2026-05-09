import os
import time
from datetime import datetime, timedelta
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

if not URL or not KEY:
    print("Error: Supabase credentials missing.")
    exit(1)

supabase = create_client(URL, KEY)

# CONFIGURATION
STORAGE_BUCKET = "studio-assets"
MAX_STORAGE_MB = 900 # 90% of 1GB
MAX_AGE_DAYS = 45

def run_cleanup():
    print(f"\n◈ INITIALIZING STUDIO PULSE CLEANUP [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ◈")
    
    try:
        # 1. TIME-BASED CLEANUP (DATABASE & STORAGE)
        cutoff_date = (datetime.now() - timedelta(days=MAX_AGE_DAYS)).isoformat()
        print(f"Checking for pulses older than {MAX_AGE_DAYS} days (Cutoff: {cutoff_date})...")
        
        # Get old pulses
        old_pulses = supabase.table("studio_heartbeat").select("*").lt("created_at", cutoff_date).execute()
        
        if old_pulses.data:
            print(f"Found {len(old_pulses.data)} expired pulses. Purging...")
            for pulse in old_pulses.data:
                # Extract storage path from mood_tag (it's the 3rd element)
                parts = pulse.get('mood_tag', '').split('|')
                if len(parts) > 2 and parts[2]:
                    asset_url = parts[2]
                    # Convert public URL back to storage path
                    # URL format: .../object/public/studio-assets/pulses/12345.mp4
                    storage_path = asset_url.split(f"{STORAGE_BUCKET}/")[-1]
                    try:
                        supabase.storage.from_(STORAGE_BUCKET).remove([storage_path])
                    except: pass
                
                # Delete from DB
                supabase.table("studio_heartbeat").delete().eq("id", pulse['id']).execute()
            print("Time-based purge complete.")
        else:
            print("No expired pulses found.")

        # 2. CAPACITY-BASED CLEANUP
        print("Analyzing storage capacity...")
        files = supabase.storage.from_(STORAGE_BUCKET).list("pulses", {"limit": 1000})
        
        total_size_bytes = sum(f.get('metadata', {}).get('size', 0) for f in files)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        print(f"Current Pulse Storage: {total_size_mb:.2f} MB / {MAX_STORAGE_MB} MB limit.")
        
        if total_size_mb > MAX_STORAGE_MB:
            print("⚠️ CAPACITY ALERT: Storage > 90%. Purging oldest files...")
            # Sort files by created_at (oldest first)
            files.sort(key=lambda x: x.get('created_at', ''))
            
            bytes_to_clear = (total_size_mb - (MAX_STORAGE_MB * 0.8)) * 1024 * 1024
            cleared_so_far = 0
            
            for f in files:
                if cleared_so_far >= bytes_to_clear: break
                
                path = f"pulses/{f['name']}"
                try:
                    supabase.storage.from_(STORAGE_BUCKET).remove([path])
                    # Also try to find and delete the DB entry for this file
                    # This is tricky because we'd need to match the URL
                    cleared_so_far += f.get('metadata', {}).get('size', 0)
                except: pass
            
            print(f"Capacity purge complete. Cleared {cleared_so_far / (1024*1024):.2f} MB.")
        else:
            print("Storage capacity within safe parameters.")

    except Exception as e:
        print(f"Cleanup Error: {e}")

if __name__ == "__main__":
    run_cleanup()
