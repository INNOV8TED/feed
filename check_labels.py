import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def main():
    res = supabase.table("studio_heartbeat").select("action_label").execute()
    labels = [p["action_label"] for p in res.data if p.get("action_label")]
    unique_labels = sorted(list(set(labels)))
    
    print(">>> Unique Labels in Database:")
    for l in unique_labels:
        count = labels.count(l)
        print(f"--- '{l}' ({count})")

if __name__ == "__main__":
    main()
