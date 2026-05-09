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
            self.wfile.write(b"Missing environment variables.")
            return

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        time_limit = (datetime.utcnow() - timedelta(hours=12)).isoformat()

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

        # 3. Fetch Images (Prioritizing HERO_)
        try:
            files = supabase.storage.from_("studio-assets").list()
            hero_images = []
            regular_images = []
            
            for f in files:
                if any(f['name'].lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    url = supabase.storage.from_("studio-assets").get_public_url(f['name'])
                    if f['name'].upper().startswith("HERO_"):
                        hero_images.append(url)
                    else:
                        regular_images.append(url)
            
            # Load images
            source_images = []
            bg_image = None
            
            # Pick a Hero for the background if possible
            if hero_images:
                r = requests.get(random.choice(hero_images))
                bg_image = Image.open(BytesIO(r.content)).convert("RGBA")
            
            # Load support images
            random.shuffle(regular_images)
            for url in regular_images[:10]:
                r = requests.get(url)
                if r.status_code == 200:
                    source_images.append(Image.open(BytesIO(r.content)).convert("RGBA"))
        except:
            source_images = []
            bg_image = None

        # 4. Assemble Collage
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), (15, 15, 20, 255))
        
        # 4a. Draw Base
        if bg_image:
            scale = max(WIDTH/bg_image.width, HEIGHT/bg_image.height)
            bg_image = bg_image.resize((int(bg_image.width*scale), int(bg_image.height*scale)))
            canvas.paste(bg_image, ((WIDTH-bg_image.width)//2, (HEIGHT-bg_image.height)//2))
            # Overlay a slight dark tint
            tint = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,100))
            canvas.paste(tint, (0,0), tint)
        
        # 4b. Draw Supporting Collage
        if source_images:
            for _ in range(12):
                img = random.choice(source_images)
                w, h = img.size
                cw, ch = int(w * 0.8), int(h * 0.8)
                img = img.crop((random.randint(0, w-cw), random.randint(0, h-ch), cw, ch))
                scale = random.uniform(1.2, 2.8)
                img = img.resize((int(img.width * scale), int(img.height * scale)))
                img.putalpha(random.randint(120, 200))
                canvas.paste(img, (random.randint(-200, WIDTH), random.randint(-200, HEIGHT)), img)

        # 5. Dynamic Stephen Sprite Selection
        sprite_map = {
            "LANNA": "stephen_lanna.png",
            "SCARLETT": "stephen_burlesque.png",
            "DEER": "stephen_deer.png",
            "DFP": "stephen_podcast.png",
            "BLUE CHROMATIC": "stephen_synth.png"
        }
        sprite_file = "stephen_focus.png" # Default
        for key, val in sprite_map.items():
            if key in dominant_project:
                sprite_file = val
                break
        
        try:
            r_sprite = requests.get(f"https://feed.in-no-v8.com/{sprite_file}")
            sprite = Image.open(BytesIO(r_sprite.content)).convert("RGBA")
            sprite_w = int(WIDTH * 0.65)
            aspect = sprite.height / sprite.width
            sprite = sprite.resize((sprite_w, int(sprite_w * aspect)))
            canvas.paste(sprite, (WIDTH - sprite.width + 80, HEIGHT - sprite.height + 80), sprite)
        except: pass

        # 6. Branding & Save
        draw = ImageDraw.Draw(canvas)
        draw.text((60, 60), f"STUDIO PULSE: {dominant_project}", fill=(0, 255, 180, 255))
        
        final_card = canvas.convert("RGB")
        output = BytesIO()
        final_card.save(output, format="JPEG", quality=92)
        output.seek(0)
        
        card_name = f"roundup_{int(datetime.now().timestamp())}.jpg"
        supabase.storage.from_("studio-assets").upload(path=f"roundups/{card_name}", file=output.read())
        final_url = supabase.storage.from_("studio-assets").get_public_url(f"roundups/{card_name}")

        # 7. Broadcast
        headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
        requests.post("https://api.buffer.com", json={
            "query": "mutation($i:CreatePostInput!){createPost(input:$i){...on PostActionSuccess{post{id}}}}",
            "variables": {"i": {
                "text": caption,
                "channelId": BUFFER_PROFILE_ID,
                "schedulingType": "automatic",
                "assets": {"images": [{"url": final_url}]},
                "metadata": {"instagram": {"type": "story"}}
            }}
        }, headers=headers)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "project": dominant_project}).encode())
        return
