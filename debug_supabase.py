import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def main():
    # 1. Fetch one pulse
    res = supabase.table("studio_heartbeat").select("*").limit(1).execute()
    if not res.data:
        print("No data found.")
        return
    
    pulse = res.data[0]
    original_label = pulse["action_label"]
    pid = pulse["id"]
    
    print(f">>> Found pulse {pid} with label: '{original_label}'")
    
    # 2. Try to update it
    new_label = "DEEP DEBUG TEST"
    print(f">>> Attempting update to '{new_label}'...")
    
    update_res = supabase.table("studio_heartbeat").update({"action_label": new_label}).eq("id", pid).execute()
    print(f">>> Update Response: {update_res}")
    
    # 3. Fetch it again to verify
    verify_res = supabase.table("studio_heartbeat").select("*").eq("id", pid).execute()
    verified_label = verify_res.data[0]["action_label"]
    
    print(f">>> Verified label after update: '{verified_label}'")
    
    # 4. Revert it
    supabase.table("studio_heartbeat").update({"action_label": original_label}).eq("id", pid).execute()
    print(">>> Reverted.")

if __name__ == "__main__":
    main()
