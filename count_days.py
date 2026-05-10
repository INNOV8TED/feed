import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

def main():
    res = supabase.table("studio_heartbeat").select("created_at").execute()
    counts = {}
    for p in res.data:
        date = p["created_at"][:10]
        counts[date] = counts.get(date, 0) + 1
    
    print(">>> Pulse counts by day:")
    for d in sorted(counts.keys(), reverse=True):
        print(f"--- {d}: {counts[d]}")

if __name__ == "__main__":
    main()
