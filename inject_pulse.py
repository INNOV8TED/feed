from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

try:
    print(">>> Manual Pulse Injection: Dr Drive f...")
    data = {
        "project_name": "Dr Drive",
        "action_label": "Deep in the Edit",
        "mood_tag": "focused|Neural link stable.||Premiere Pro|The best way to predict the future is to create it. – Peter Drucker",
        "source": "Manual-Injection"
    }
    supabase.table("studio_heartbeat").insert(data).execute()
    print(">>> Success! Pulse injected.")
except Exception as e:
    print(f">>> [ERROR] {e}")
