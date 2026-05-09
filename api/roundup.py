import os
import requests
import json
import random
import time
from io import BytesIO
from datetime import datetime, timedelta
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont
from http.server import BaseHTTPRequestHandler

# Collage dimensions (IG Story)
WIDTH, HEIGHT = 1080, 1920

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
        BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")

        if not all([SUPABASE_URL, SUPABASE_KEY, BUFFER_TOKEN, BUFFER_PROFILE_ID]):
            self.wfile.write(json.dumps({"error": "Missing environment variables"}).encode())
            return

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        results = []

        # ◈ DOUBLE ROUNDUP: Run generation twice to push two distinct stories ◈
        for run_idx in range(2):
            try:
                # 0. Initialize Canvas
                canvas = Image.new("RGBA", (WIDTH, HEIGHT), (10, 10, 15, 255))
                draw = ImageDraw.Draw(canvas)
                
                # Draw Cinematic Gradient (Base Layer)
                for i in range(HEIGHT):
                    r = int(10 + (25 - 10) * i / HEIGHT)
                    g = int(10 + (35 - 10) * i / HEIGHT)
                    b = int(15 + (45 - 15) * i / HEIGHT)
                    draw.line([(0, i), (WIDTH, i)], fill=(r, g, b, 255))

                # 1. Fetch Archive.org Magazines (Secret Sauce)
                def fetch_archive_mags(query="popular mechanics", count=10):
                    try:
                        page = random.randint(1, 8)
                        q = f"collection:(magazine_rack) AND ({query}) AND year:[0 TO 1977]"
                        url = f"https://archive.org/advancedsearch.php?q={requests.utils.quote(q)}&fl[]=identifier&output=json&rows={count}&page={page}&sort[]=downloads+desc"
                        res = requests.get(url, timeout=10).json()
                        docs = res.get('response', {}).get('docs', [])
                        return [f"https://archive.org/services/img/{d['identifier']}" for d in docs if d.get('identifier')]
                    except: return []

                # 2. Analyze Activity (Fetch last 30 for diversity)
                try:
                    ping_res = supabase.table("studio_heartbeat").select("*").order("id", desc=True).limit(30).execute()
                    pings = ping_res.data
                except: pings = []

                project_counts = {}
                milestones = 0
                for p in pings:
                    name = p.get('project_name', 'General Lab').upper()
                    project_counts[name] = project_counts.get(name, 0) + 1
                    if p.get('is_milestone'): milestones += 1
                
                dominant_project = max(project_counts, key=project_counts.get) if project_counts else "INNOV8"
                
                # Dynamic Caption
                captions = [
                    f"◈ STUDIO PULSE / Double-time in the lab focusing on #{dominant_project}.",
                    f"◈ ROUNDUP / Deep in the weeds of #{dominant_project}. Processing assets..."
                ]
                caption = captions[run_idx]
                if milestones > 0: caption += f" Hit {milestones} major milestones today. 🔥"
                caption += "\n\nLive: feed.in-no-v8.com"
                
                # 3. Gather Image Sources
                archive_mags = fetch_archive_mags(dominant_project.lower() if dominant_project != "INNOV8" else "popular mechanics")
                
                fallback_mags = [
                    "https://feed.in-no-v8.com/acam_sprite.png",
                    "https://feed.in-no-v8.com/lanna_sprite.png",
                    "https://feed.in-no-v8.com/stephen_synth.png"
                ]

                hero_images = []
                regular_images = []
                try:
                    files = supabase.storage.from_("studio-assets").list(options={"limit": 50})
                    for f in files:
                        name = f['name']
                        if any(name.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                            url = supabase.storage.from_("studio-assets").get_public_url(name)
                            if "HERO" in name.upper(): hero_images.append(url)
                            else: regular_images.append(url)
                except: pass

                all_collage_assets = archive_mags + regular_images + fallback_mags
                random.shuffle(all_collage_assets)

                # 4. Assemble Collage
                bg_sources = archive_mags + hero_images + regular_images
                if bg_sources:
                    try:
                        bg_url = random.choice(bg_sources)
                        bg_image = Image.open(BytesIO(requests.get(bg_url, timeout=5).content)).convert("RGBA")
                        scale = max(WIDTH/bg_image.width, HEIGHT/bg_image.height)
                        bg_image = bg_image.resize((int(bg_image.width*scale), int(bg_image.height*scale)))
                        canvas.paste(bg_image, ((WIDTH-bg_image.width)//2, (HEIGHT-bg_image.height)//2))
                        canvas.paste(Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,90)), (0,0), Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,90)))
                    except: pass
                
                for url in all_collage_assets[:16]:
                    try:
                        img = Image.open(BytesIO(requests.get(url, timeout=5).content)).convert("RGBA")
                        w, h = img.size
                        cw, ch = int(w * 0.9), int(h * 0.9)
                        img = img.crop((random.randint(0, w-cw), random.randint(0, h-ch), w, h))
                        scale = random.uniform(1.2, 2.8)
                        img = img.resize((int(img.width * scale), int(img.height * scale)))
                        img.putalpha(random.randint(180, 250))
                        img = img.rotate(random.randint(-15, 15), expand=True)
                        canvas.paste(img, (random.randint(-WIDTH//4, WIDTH), random.randint(-HEIGHT//4, HEIGHT)), img)
                    except: continue

                # 5. Sprite (FRONT LAYER)
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
                    sprite_w = int(WIDTH * 0.8)
                    sprite = sprite.resize((sprite_w, int(sprite_w * (sprite.height/sprite.width))))
                    canvas.paste(sprite, (WIDTH - sprite.width + 50, HEIGHT - sprite.height + 50), sprite)
                except: pass

                # 6. Save and Upload
                draw = ImageDraw.Draw(canvas)
                draw.text((60, 60), f"STUDIO PULSE / SEQUENCE #{run_idx + 1}", fill=(0, 255, 180, 255))
                
                output = BytesIO()
                canvas.convert("RGBA").save(output, format="PNG")
                output.seek(0)
                
                file_name = f"roundup_{int(time.time())}_{run_idx}.png"
                supabase.storage.from_("studio-assets").upload(path=file_name, file=output.read(), file_options={"content-type": "image/png"})
                final_url = supabase.storage.from_("studio-assets").get_public_url(file_name)

                # 7. Push to Buffer (Automatic scheduling handles the rest)
                headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
                mutation = """
                mutation CreatePost($i: CreatePostInput!) {
                  createPost(input: $i) {
                    ... on PostActionSuccess { post { id } }
                    ... on MutationError { message }
                  }
                }
                """
                payload = {
                    "query": mutation,
                    "variables": {"i": {
                        "text": caption,
                        "channelId": BUFFER_PROFILE_ID,
                        "schedulingType": "automatic",
                        "mode": "addToQueue",
                        "assets": {"images": [{"url": final_url}]},
                        "metadata": {"instagram": {"type": "story", "shouldShareToFeed": False}}
                    }}
                }
                
                buffer_res = requests.post("https://api.buffer.com", json=payload, headers=headers)
                results.append({"run": run_idx, "status": buffer_res.status_code, "url": final_url})

            except Exception as e:
                results.append({"run": run_idx, "error": str(e)})

        self.wfile.write(json.dumps({"summary": "Double Story Generation Complete", "results": results}).encode())
