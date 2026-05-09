from http.server import BaseHTTPRequestHandler
import os
import requests
import json
import random
import time
from io import BytesIO
from datetime import datetime, timedelta
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Configuration (Supporting both standard and NEXT_PUBLIC naming)
        SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
        BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")
        WIDTH, HEIGHT = 1080, 1920
        
        # Diagnostics
        missing = []
        if not SUPABASE_URL: missing.append("SUPABASE_URL")
        if not SUPABASE_KEY: missing.append("SUPABASE_KEY")
        if not BUFFER_TOKEN: missing.append("BUFFER_TOKEN")
        if not BUFFER_PROFILE_ID: missing.append("BUFFER_PROFILE_ID")

        if missing:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Missing environment variables: {', '.join(missing)}".encode())
            return

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Fix: Remove microseconds for Supabase compatibility
        time_limit = (datetime.utcnow() - timedelta(hours=12)).replace(microsecond=0).isoformat()

        # 0. Initialize Canvas (Early Fallback)
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), (10, 10, 15, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Draw Cinematic Gradient (Base Layer)
        for i in range(HEIGHT):
            r = int(10 + (25 - 10) * i / HEIGHT)
            g = int(10 + (35 - 10) * i / HEIGHT)
            b = int(15 + (45 - 15) * i / HEIGHT)
            draw.line([(0, i), (WIDTH, i)], fill=(r, g, b, 255))

        # 2. Analyze Dominant Project & Narrative
        try:
            ping_res = supabase.table("studio_heartbeat").select("*").gte("created_at", time_limit).execute()
            pings = ping_res.data
        except:
            pings = []

        project_counts = {}
        milestones = 0
        for p in pings:
            name = p.get('project_name', 'General Lab').upper()
            project_counts[name] = project_counts.get(name, 0) + 1
            if p.get('is_milestone'): milestones += 1
        
        dominant_project = max(project_counts, key=project_counts.get) if project_counts else "INNOV8"
        
        # Draft Caption
        caption = f"A massive day in the lab focusing on #{dominant_project}. "
        if project_counts:
            details = [f"{c} updates on {p}" for p, c in project_counts.items()]
            caption += f"({', '.join(details)}). "
        if milestones > 0:
            caption += f"Hit {milestones} major milestones. The shots are fire. 🔥"
        else:
            caption += "Deep in the weeds of the creative process. 🛠️"
        caption += "\n\nLive Pulse: feed.in-no-v8.com"

        # 3. Fetch Images (Prioritizing HERO_ and MAG_)
        hero_images = []
        regular_images = []
        
        # Fallback assets if Supabase is empty
        fallback_mags = [
            "https://feed.in-no-v8.com/acam_sprite.png",
            "https://feed.in-no-v8.com/lanna_sprite.png",
            "https://feed.in-no-v8.com/stephen_synth.png"
        ]

        try:
            files = supabase.storage.from_("studio-assets").list(options={"limit": 100})
            for f in files:
                name = f['name']
                if any(name.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    url = supabase.storage.from_("studio-assets").get_public_url(name)
                    if "HERO" in name.upper():
                        hero_images.append(url)
                    elif "MAG" in name.upper() or "177" in name or "ROUNDUP" in name.upper():
                        regular_images.append(url)
                    else:
                        regular_images.append(url)
        except Exception as e:
            print(f"Supabase list failed: {e}")

        if not regular_images:
            regular_images = fallback_mags

        # 4. Assemble Collage
        try:
            # Load Background Image
            bg_image = None
            bg_sources = hero_images + regular_images
            if bg_sources:
                for _ in range(3):
                    try:
                        bg_url = random.choice(bg_sources)
                        res = requests.get(bg_url, timeout=5)
                        bg_image = Image.open(BytesIO(res.content)).convert("RGBA")
                        break
                    except: continue

            # 4b. Draw Base Image
            if bg_image:
                scale = max(WIDTH/bg_image.width, HEIGHT/bg_image.height)
                bg_image = bg_image.resize((int(bg_image.width*scale), int(bg_image.height*scale)))
                canvas.paste(bg_image, ((WIDTH-bg_image.width)//2, (HEIGHT-bg_image.height)//2))
                # Lighter tint (70 instead of 140) to keep background visible
                tint = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,70))
                canvas.paste(tint, (0,0), tint)
            
            # 4c. Draw Supporting Collage (UNDER the sprite)
            collage_sources = regular_images + fallback_mags
            random.shuffle(collage_sources)
            for url in collage_sources[:15]:
                try:
                    img_res = requests.get(url, timeout=5)
                    img = Image.open(BytesIO(img_res.content)).convert("RGBA")
                    w, h = img.size
                    cw, ch = int(w * 0.9), int(h * 0.9)
                    img = img.crop((random.randint(0, w-cw), random.randint(0, ch-ch), w, h))
                    scale = random.uniform(1.0, 2.5)
                    img = img.resize((int(img.width * scale), int(img.height * scale)))
                    img.putalpha(random.randint(150, 230)) # More opaque
                    img = img.rotate(random.randint(-15, 15), expand=True)
                    canvas.paste(img, (random.randint(-WIDTH//4, WIDTH), random.randint(-HEIGHT//4, HEIGHT)), img)
                except: continue
        except Exception as e:
            print(f"Collage assembly failed: {e}")

        # 5. Dynamic Stephen Sprite Selection (FRONT LAYER)
        sprite_map = {
            "LANNA": "stephen_lanna.png",
            "SCARLETT": "stephen_burlesque.png",
            "DEER": "stephen_deer.png",
            "DFP": "stephen_podcast.png",
            "BLUE CHROMATIC": "stephen_synth.png"
        }
        sprite_file = "stephen_focus.png"
        for key, val in sprite_map.items():
            if key in dominant_project:
                sprite_file = val
                break
        
        try:
            r_sprite = requests.get(f"https://feed.in-no-v8.com/{sprite_file}", timeout=10)
            sprite = Image.open(BytesIO(r_sprite.content)).convert("RGBA")
            sprite_w = int(WIDTH * 0.75) # Larger sprite
            aspect = sprite.height / sprite.width
            sprite = sprite.resize((sprite_w, int(sprite_w * aspect)))
            # Position at the very front
            canvas.paste(sprite, (WIDTH - sprite.width + 50, HEIGHT - sprite.height + 50), sprite)
        except Exception as e: 
            print(f"Sprite loading failed: {e}")

        # 6. Save and Upload Final Card
        draw = ImageDraw.Draw(canvas)
        draw.text((60, 60), f"STUDIO PULSE: {dominant_project}", fill=(0, 255, 180, 255))
        
        final_card = canvas.convert("RGBA")
        output = BytesIO()
        final_card.save(output, format="PNG")
        output.seek(0)
        
        card_name = f"roundup_{int(datetime.now().timestamp())}.png"
        # Fix: Upload with explicit content-type
        try:
            supabase.storage.from_("studio-assets").upload(
                path=card_name, 
                file=output.read(),
                file_options={"content-type": "image/png"}
            )
            final_url = supabase.storage.from_("studio-assets").get_public_url(card_name)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Storage Upload Failed: {e}".encode())
            return
        
        # Add a small delay to ensure the file is ready for Buffer's crawler
        time.sleep(3)

        headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
        buffer_res = requests.post("https://api.buffer.com", json={
            "query": "mutation($i:CreatePostInput!){createPost(input:$i){...on PostActionSuccess{post{id}} ...on MutationError{message}}}",
            "variables": {"i": {
                "text": caption,
                "channelId": BUFFER_PROFILE_ID,
                "schedulingType": "automatic",
                "mode": "addToQueue",
                "assets": {"images": [{"url": final_url}]},
                "metadata": {"instagram": {
                    "type": "story",
                    "shouldShareToFeed": False
                }}
            }}
        }, headers=headers)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "project": dominant_project, "card_url": final_url, "buffer": buffer_res.json()}).encode())
        return
