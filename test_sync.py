from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

try:
    print(">>> Testing Supabase Connection...")
    # Try a simple fetch to see columns
    res = supabase.table("studio_heartbeat").select("*").limit(1).execute()
    if res.data:
        print(f">>> Success! Columns: {list(res.data[0].keys())}")
    else:
        print(">>> Table is empty.")
    
    # Try a test insert
    test_data = {
        "project_name": "DIAGNOSTIC_TEST",
        "action_label": "Testing Neural Link",
        "mood_tag": "focused|Test sync||Creative Engine|Quote",
        "source": "Diagnostics"
    }
    print(">>> Attempting Test Insert...")
    ins_res = supabase.table("studio_heartbeat").insert(test_data).execute()
    print(f">>> Insert Success! ID: {ins_res.data[0]['id']}")
except Exception as e:
    print(f">>> [ERROR] {str(e)}")
