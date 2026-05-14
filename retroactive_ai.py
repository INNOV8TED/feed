import os
import json
import requests
import base64
from supabase import create_client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

supabase = create_client(URL, KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_visual_caption(image_url):
    try:
        print(f">>> Downloading: {image_url}")
        img_data = requests.get(image_url).content
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        print(f">>> AI Analyzing...")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this studio work in 5-8 words for a professional social media feed. Focus on the mood and technical aspect. No hashtags. Example: 'Refining atmospheric lighting in the Lanna temple.'"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ],
                }
            ],
            max_tokens=50,
        )
        return response.choices[0].message.content.strip().strip('"')
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def main():
    print("[RETROACTIVE AI] Fetching last 10 social pulses...")
    
    response = supabase.table("studio_heartbeat")\
        .select("*")\
        .or_("project_name.ilike.%LANNA%,project_name.ilike.%SOCIAL%,project_name.ilike.%MEMORIES%")\
        .order("created_at", desc=True)\
        .limit(10)\
        .execute()
    
    pulses = response.data
    if not pulses:
        print("No pulses found.")
        return

    for pulse in pulses:
        pid = pulse["id"]
        parts = pulse["mood_tag"].split("|")
        if len(parts) < 3: continue
        asset_url = parts[2]
        if not asset_url or not asset_url.startswith("http") or asset_url.lower().endswith(('.mp4', '.mov')):
            continue

        caption = generate_visual_caption(asset_url)
        if caption:
            print(f"Success! Pulse {pid} -> '{caption}'")
            supabase.table("studio_heartbeat")\
                .update({"action_label": caption})\
                .eq("id", pid)\
                .execute()

    print("[COMPLETE] Retroactive AI update finished.")

if __name__ == "__main__":
    main()
