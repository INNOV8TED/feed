
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

res = supabase.table("studio_heartbeat").select("*").order("created_at", desc=True).limit(5).execute()
for row in res.data:
    print(f"{row['created_at']} | {row['project_name']} | {row['action_label']}")
