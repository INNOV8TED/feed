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
                MAG_CATEGORIES = [
                    "popular mechanics", "byte magazine", "omni magazine", "science & mechanics",
                    "electronics world", "modern screen", "life magazine", "radio-electronics",
                    "high fidelity", "computermusic", "national geographic", "art news"
                ]
                mag_query = random.choice(MAG_CATEGORIES)
                archive_mags = fetch_archive_mags(mag_query)
                
                fallback_mags = [
                    "https://feed.in-no-v8.com/acam_sprite.png",
                    "https://feed.in-no-v8.com/lanna_sprite.png",
                    "https://feed.in-no-v8.com/stephen_synth.png"
                ]

                hero_images = []
                regular_images = []
                try:
                    for p in pings:
                        parts = p.get('mood_tag', '').split('|')
                        if len(parts) > 2 and parts[2]:
                            url = parts[2]
                            if any(url.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                                if "HERO" in url.upper(): hero_images.append(url)
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
                sprite_pool = [
                    "stephen_artist.png", "stephen_burlesque.png", "stephen_celebration.png", 
                    "stephen_deer.png", "stephen_focus.png", "stephen_hacker.png", 
                    "stephen_lanna.png", "stephen_podcast.png", "stephen_synth.png",
                    "stephen_rand1.png", "stephen_rand2.png", "stephen_rand3.png", 
                    "stephen_rand4.png", "stephen_rand5.png", "stephen_rand6.png"
                ]
                
                # Try project match first, then fallback to random
                sprite_map = {
                    "LANNA": "stephen_lanna.png",
                    "SCARLETT": "stephen_burlesque.png",
                    "DEER": "stephen_deer.png",
                    "DFP": "stephen_podcast.png",
                    "AUDIO": "stephen_synth.png"
                }
                
                sprite_file = None
                for key, val in sprite_map.items():
                    if key in dominant_project:
                        sprite_file = val
                        break
                
                if not sprite_file:
                    sprite_file = random.choice(sprite_pool)
                
                try:
                    r_sprite = requests.get(f"https://feed.in-no-v8.com/{sprite_file}", timeout=10)
                    sprite = Image.open(BytesIO(r_sprite.content)).convert("RGBA")
                    sprite_w = int(WIDTH * 0.85)
                    sprite = sprite.resize((sprite_w, int(sprite_w * (sprite.height/sprite.width))))
                    canvas.paste(sprite, (WIDTH - sprite.width + 100, HEIGHT - sprite.height + 100), sprite)
                except: pass

                # 6. Save and Upload
                draw = ImageDraw.Draw(canvas)
                draw.text((60, 60), f"STUDIO PULSE / SEQUENCE #{run_idx + 1}", fill=(0, 255, 180, 255))
                
                output = BytesIO()
                canvas.convert("RGBA").save(output, format="PNG")
                output.seek(0)
                
                file_name = f"roundup_{int(time.time())}_{run_idx}.png"
                
                # Upload to Knownhost FTP
                import ftplib
                FTP_HOST = "ftp.in-no-v8.com"
                FTP_USER = "innov8co"
                FTP_PASS = "%odn*fr*l4a7$e"
                
                ftp = ftplib.FTP_TLS(FTP_HOST)
                ftp.login(FTP_USER, FTP_PASS)
                ftp.prot_p()
                
                remote_dir = "/in-no-v8.world/vault/studio-assets"
                
                # Ensure remote directory exists
                parts = remote_dir.split('/')
                current = ""
                for part in parts:
                    if not part:
                        continue
                    current = f"{current}/{part}"
                    try:
                        ftp.mkd(current)
                    except Exception:
                        pass
                
                remote_path = f"{remote_dir}/{file_name}"
                # output.seek(0) was already run, read is perfect
                ftp.storbinary(f'STOR {remote_path}', output)
                ftp.quit()
                
                final_url = f"https://in-no-v8.world/vault/studio-assets/{file_name}"

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
