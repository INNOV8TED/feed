import os, time, pyautogui
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

try:
    print(">>> Manual Vision Syncing...")
    # 1. Capture Screen
    shot = pyautogui.screenshot()
    shot = shot.resize((1280, 720))
    shot.save("temp_test.jpg", "JPEG", quality=70)
    
    # 2. Upload to Storage
    with open("temp_test.jpg", 'rb') as f:
        path = f"pulses/test_{int(time.time())}.jpg"
        supabase.storage.from_('studio-assets').upload(path, f.read())
        url = supabase.storage.from_('studio-assets').get_public_url(path)
    
    # 3. Inject Pulse
    data = {
        "project_name": "Studio Pulse",
        "action_label": "System Diagnostic",
        "mood_tag": f"focused|Neural link stable.|{url}|TEST ENGINE|Vision pipeline active.",
        "source": "Manual-Injection"
    }
    supabase.table("studio_heartbeat").insert(data).execute()
    print(f">>> Success! Vision Linked: {url}")
    if os.path.exists("temp_test.jpg"): os.remove("temp_test.jpg")
except Exception as e:
    print(f">>> [ERROR] {e}")
