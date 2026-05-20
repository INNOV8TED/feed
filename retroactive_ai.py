import os
import json
import requests
import base64
import random
from supabase import create_client
from gcp_gemini_client import call_gemini, get_access_token
from dotenv import load_dotenv
import datetime

# Load environment
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(URL, KEY)
openai_client = get_access_token() is not None

def generate_creative_title(filename):
    """Uses AI to turn generic filenames into evocative studio titles."""
    if not openai_client:
        return filename.replace("_", " ").title()
    try:
        clean_name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
        title = call_gemini(
            prompt=f"Filename: {clean_name}",
            system_instruction="You are a creative director. Turn generic filenames into 2-5 word evocative, professional studio titles. No quotes. No hashtags. Just the title.",
            model="gemini-2.5-flash"
        )
        if title:
            return title.strip().replace('"', '')
        else:
            raise Exception("Gemini return was empty")
    except:
        return filename.replace("_", " ").title()

def generate_visual_caption(image_url):
    """Analyzes an image to generate a caption."""
    if not openai_client: return None
    try:
        print(f">>> AI Analyzing Image: {image_url}")
        img_data = requests.get(image_url).content
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        caption = call_gemini(
            prompt="Describe this work in 5-8 words. Professional studio tone. No hashtags.",
            image_data=base64_image,
            model="gemini-2.5-flash"
        )
        if caption:
            return caption.strip().strip('"')
        else:
            raise Exception("Gemini return was empty")
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def main():
    print("[RETROACTIVE AI] Fetching last 50 pulses...")
    
    # Fetch from studio_heartbeat
    response = supabase.table("studio_heartbeat")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(50)\
        .execute()
    
    pulses = response.data
    if not pulses:
        print("No pulses found.")
        return

    for pulse in pulses:
        pid = pulse["id"]
        current_label = pulse.get("action_label", "")
        project_name = pulse.get("project_name", "")
        
        # Check if it looks like a fallback name (e.g. "Image Pulse 12345" or simple Title Case)
        is_fallback = any(x in current_label.lower() for x in ["image pulse", "audio pulse", "clip", "video pulse"]) or current_label == project_name
        
        if not is_fallback:
            print(f"Skipping {pid} (Already named: '{current_label}')")
            continue

        print(f"◈ Processing Pulse {pid} ({project_name})...")
        
        parts = pulse["mood_tag"].split("|")
        asset_url = parts[2] if len(parts) >= 3 else ""
        
        new_label = None
        if asset_url and asset_url.startswith("http") and not asset_url.lower().endswith(('.mp4', '.mov')):
            # It's an image, use vision if possible
            new_label = generate_visual_caption(asset_url)
        
        if not new_label:
            # Fallback to creative title from project name
            new_label = generate_creative_title(project_name)

        if new_label and new_label != current_label:
            print(f"   Success! '{current_label}' -> '{new_label}'")
            # Update studio_heartbeat
            supabase.table("studio_heartbeat").update({"action_label": new_label}).eq("id", pid).execute()
            # Also try to update feed table if it exists there
            try:
                supabase.table("feed").update({"action_label": new_label}).eq("project_name", project_name).eq("asset_url", asset_url).execute()
            except: pass

    print("[COMPLETE] Retroactive AI update finished.")

if __name__ == "__main__":
    main()
