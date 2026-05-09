from http.server import BaseHTTPRequestHandler
import os
import requests
import json
import random
from io import BytesIO
from datetime import datetime, timedelta
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Configuration
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
        BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")
        
        WIDTH, HEIGHT = 1080, 1920
        
        if not all([SUPABASE_URL, SUPABASE_KEY, BUFFER_TOKEN, BUFFER_PROFILE_ID]):
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Missing environment variables.")
            return

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 2. Fetch Daily Images from Storage
        try:
            files = supabase.storage.from_("studio-assets").list()
            # Filter for images uploaded today (or just take the latest 10)
            image_urls = []
            for f in files:
                if any(f['name'].lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    url = supabase.storage.from_("studio-assets").get_public_url(f['name'])
                    image_urls.append(url)
            
            # Limit to 10 for performance
            random.shuffle(image_urls)
            source_images = []
            for url in image_urls[:10]:
                r = requests.get(url)
                if r.status_code == 200:
                    source_images.append(Image.open(BytesIO(r.content)).convert("RGBA"))
        except Exception as e:
            print(f"Image fetch error: {e}")
            source_images = []

        # 3. Build Collage
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), (10, 10, 15, 255)) # Dark base
        
        if source_images:
            # Simple Collage Logic (Ported from your Machine)
            for _ in range(15):
                img = random.choice(source_images)
                # Random crop and scale
                w, h = img.size
                cw, ch = int(w * 0.7), int(h * 0.7)
                img = img.crop((random.randint(0, w-cw), random.randint(0, h-ch), cw, ch))
                scale = random.uniform(1.0, 2.5)
                img = img.resize((int(img.width * scale), int(img.height * scale)))
                
                # Paste with transparency
                img.putalpha(random.randint(100, 180))
                canvas.paste(img, (random.randint(-200, WIDTH), random.randint(-200, HEIGHT)), img)

        # 4. Overlay Stephen Sprite
        try:
            sprite_url = "https://feed.in-no-v8.com/stephen_focus.png" # Default
            # Attempt to pull a vertical one if exists
            r_sprite = requests.get(sprite_url)
            sprite = Image.open(BytesIO(r_sprite.content)).convert("RGBA")
            # Scale sprite to fit nicely in corner
            sprite_w = int(WIDTH * 0.6)
            aspect = sprite.height / sprite.width
            sprite = sprite.resize((sprite_w, int(sprite_w * aspect)))
            canvas.paste(sprite, (WIDTH - sprite.width + 50, HEIGHT - sprite.height + 50), sprite)
        except Exception as e:
            print(f"Sprite error: {e}")

        # 5. Add Text Branding
        draw = ImageDraw.Draw(canvas)
        # We use a default font if custom isn't loaded
        text = "STUDIO PULSE ROUNDUP"
        draw.text((60, 60), text, fill=(0, 255, 180, 255))
        draw.text((60, 110), datetime.now().strftime("%Y-%m-%d"), fill=(255, 255, 255, 150))

        # 6. Save and Upload Final Card
        final_card = canvas.convert("RGB")
        output = BytesIO()
        final_card.save(output, format="JPEG", quality=90)
        output.seek(0)
        
        card_filename = f"roundup_{datetime.now().strftime('%Y%m%d_%H%M')}.jpg"
        supabase.storage.from_("studio-assets").upload(
            path=f"roundups/{card_filename}",
            file=output.read(),
            file_options={"content-type": "image/jpeg"}
        )
        final_url = supabase.storage.from_("studio-assets").get_public_url(f"roundups/{card_filename}")

        # 7. Post to Buffer
        buffer_url = "https://api.buffer.com"
        query = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id } }
            ... on MutationError { message }
          }
        }
        """
        variables = {
            "input": {
                "text": "Latest from the Lab. #StudioPulse",
                "channelId": BUFFER_PROFILE_ID,
                "schedulingType": "automatic",
                "mode": "addToQueue",
                "assets": { "images": [{"url": final_url}] },
                "metadata": { "instagram": { "type": "story" } }
            }
        }
        headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
        requests.post(buffer_url, json={"query": query, "variables": variables}, headers=headers)

        # 8. Response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "card_url": final_url}).encode())
        return
