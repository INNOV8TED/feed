import os
import json
import datetime
import time
import sys
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Add current dir to path to import heartbeat functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Harden console output against Windows CP1252 Unicode crashes
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from heartbeat import broadcast_to_buffer, upload_to_supabase, generate_and_upload_thumbnail, get_video_dimensions, format_video_vertical, generate_creative_title

SOCIAL_DIR = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL"
CACHE_FILE = "studio_cache.json"
QUOTA_FILE = "buffer_quota.json"

BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")
BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")

def get_pillow_font(font_name="arial.ttf", size=24, use_devanagari=False):
    try:
        if use_devanagari:
            # Load Windows standard South Asian font collection for Devanagari/Nepalese
            win_font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", "Nirmala.ttc")
            if os.path.exists(win_font_path):
                return ImageFont.truetype(win_font_path, size)
                
        # Check standard Windows fonts folder
        win_font_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts", font_name)
        if os.path.exists(win_font_path):
            return ImageFont.truetype(win_font_path, size)
        # Fallback to loading by name
        return ImageFont.truetype(font_name, size)
    except:
        return ImageFont.load_default()

def get_place_name(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
        headers = {"User-Agent": "INNOV8-Activity-Feed/1.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        address = data.get("address", {})
        city = address.get("city") or address.get("town") or address.get("village") or address.get("suburb") or address.get("county") or "Unknown Location"
        country = address.get("country", "")
        return city, country
    except Exception as e:
        print(f"[GEOCODE ERROR] {e}")
        return "Unknown Location", ""

def create_leica_card(image_url, tag, date_str, coords, location_name=None):
    try:
        # 1. Fetch image
        resp = requests.get(image_url, timeout=30)
        img = Image.open(BytesIO(resp.content))
        
        # 2. Define Canvas sizes (Instagram Portrait: 1080x1350)
        canvas_w = 1080
        canvas_h = 1350
        canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
        
        # Margin and image boundaries
        margin = 60
        box_w = canvas_w - (margin * 2)
        box_h = canvas_h - margin - 200 # leaves 200px at bottom
        
        # Scale image to fit within box_w, box_h maintaining aspect ratio
        img.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
        
        # Center image within photo box
        img_w, img_h = img.size
        img_x = margin + (box_w - img_w) // 2
        img_y = margin + (box_h - img_h) // 2
        
        # Paste on white canvas
        canvas.paste(img, (img_x, img_y))
        
        # 3. Draw Leica styled footer
        draw = ImageDraw.Draw(canvas)
        
        # Draw Leica Left Info
        left_text = str(tag).upper().replace("_", " ")
        if location_name:
            left_text += f" | {location_name.upper()}"
            
        # Detect Devanagari/Nepali characters to dynamically switch font
        use_devanagari = any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in left_text)
        
        font_bold = get_pillow_font("arial.ttf", 26)
        font_reg = get_pillow_font("arial.ttf", 20, use_devanagari=use_devanagari)
        
        footer_y = margin + box_h + 30
        
        draw.text((margin, footer_y), "ARCHIVE RECORD", fill="black", font=font_bold)
        draw.text((margin, footer_y + 35), left_text, fill="#666666", font=font_reg)
        
        # Draw Leica Right Info
        logo_text = "INNOV8"
        lat, lng = coords[0], coords[1]
        exif_text = f"{date_str} | {lat:.2f}, {lng:.2f}"
        
        # Alignments
        logo_w = draw.textlength(logo_text, font=font_bold)
        exif_w = draw.textlength(exif_text, font=font_reg)
        
        right_x = canvas_w - margin
        
        # Draw Red Dot
        dot_r = 7
        dot_x = right_x - logo_w - 20
        dot_y = footer_y + 15
        draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill="#FF3B30")
        
        # Text draws
        draw.text((right_x - logo_w, footer_y), logo_text, fill="black", font=font_bold)
        draw.text((right_x - exif_w, footer_y + 35), exif_text, fill="#666666", font=font_reg)
        
        # Separator line
        draw.line([margin, footer_y - 15, right_x, footer_y - 15], fill="#EAEAEA", width=1)
        
        return canvas
    except Exception as e:
        print(f"[LEICA CARD GENERATION ERROR] {e}")
        return None

def get_organization_id():
    url = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {BUFFER_TOKEN}",
        "Content-Type": "application/json"
    }
    query = """
    query {
      account {
        organizations {
          id
        }
      }
    }
    """
    res = requests.post(url, json={"query": query}, headers=headers, timeout=15)
    if res.status_code != 200:
        raise RuntimeError(f"Buffer API Get Organization failed with status {res.status_code}: {res.text}")
    data = res.json()
    if "errors" in data:
        raise RuntimeError(f"Buffer GraphQL Error in Get Organization: {data['errors']}")
    orgs = data.get("data", {}).get("account", {}).get("organizations", [])
    if not orgs:
        raise RuntimeError("No Buffer organizations found for this account.")
    return orgs[0]["id"]

def get_live_scheduled_posts(profile_id):
    org_id = get_organization_id()
    url = "https://api.buffer.com"
    headers = {
        "Authorization": f"Bearer {BUFFER_TOKEN}",
        "Content-Type": "application/json"
    }
    query_posts = """
    query GetChannelPosts($orgId: OrganizationId!, $channelId: ChannelId!) {
      posts(input: { organizationId: $orgId, filter: { status: [scheduled], channelIds: [$channelId] } }) {
        edges {
          node {
            id
            text
            dueAt
          }
        }
      }
    }
    """
    variables = {"orgId": org_id, "channelId": profile_id}
    res = requests.post(url, json={"query": query_posts, "variables": variables}, headers=headers, timeout=15)
    if res.status_code != 200:
        raise RuntimeError(f"Buffer API Get Channel Posts failed with status {res.status_code}: {res.text}")
    data = res.json()
    if "errors" in data:
        raise RuntimeError(f"Buffer GraphQL Error in Get Channel Posts: {data['errors']}")
    edges = data.get("data", {}).get("posts", {}).get("edges", [])
    return [e["node"] for e in edges]

def is_inside_numbered_lanna_folder(root_path):
    normalized = os.path.normpath(root_path)
    parts = normalized.split(os.sep)
    try:
        lanna_idx = parts.index("LANNA")
        for part in parts[lanna_idx + 1:]:
            if part.isdigit():
                return True
    except ValueError:
        pass
    return False

def refill():
    print(">>> [REFILL] Starting manual Buffer replenishment (Live-Audited & Variety-Space Optimized)...")
    
    # Load Cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except Exception as e:
            print(f"[CACHE LOAD ERROR] {e}")
            
    # Standardize size_cache sub-object
    if "size_cache" not in cache:
        cache["size_cache"] = {}
    size_cache = cache["size_cache"]
    
    # Load Quota (maintained for compatibility)
    quota = {}
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, 'r') as f:
                quota = json.load(f)
        except Exception as e:
            print(f"[QUOTA LOAD ERROR] {e}")
            
    current_week = datetime.datetime.now().strftime('%Y-%W')
    refilled_count = 0

    # ----------------------------------------------------
    # 1. LANNA.WHISPERS CHANNEL REPLENISHMENT (1 Post/Day Carousel)
    # ----------------------------------------------------
    print(f"\n>>> Analyzing Lanna.whispers Queue...")
    lanna_queue = get_live_scheduled_posts(BUFFER_PROFILE_ID_LANNA)
    print(f">>> Lanna scheduled queue size: {len(lanna_queue)}/10")
    
    if len(lanna_queue) >= 10:
        print(">>> Lanna queue is at maximum capacity (10 posts). Skipping Lanna replenishment.")
    else:
        # We can add posts up to the 10-post limit
        slots_to_fill = 10 - len(lanna_queue)
        print(f">>> Found {slots_to_fill} available slot(s) in Lanna queue.")
        
        # Scan SOCIAL/LANNA for numbered directories representing carousels
        lanna_root = os.path.join(SOCIAL_DIR, "LANNA")
        numbered_dirs = []
        if os.path.exists(lanna_root):
            for entry in os.listdir(lanna_root):
                entry_path = os.path.join(lanna_root, entry)
                if os.path.isdir(entry_path) and entry.isdigit():
                    numbered_dirs.append(entry)
                    
        # Sort folders numerically (e.g. 17, 18, 19...)
        numbered_dirs.sort(key=int)
        print(f">>> Found {len(numbered_dirs)} numbered Lanna carousel folders: {numbered_dirs}")
        
        for folder_name in numbered_dirs:
            if slots_to_fill <= 0:
                break
                
            cache_key = f"CAROUSEL_{folder_name}"
            # Check if this folder has already been processed
            if cache_key in size_cache:
                print(f"  - Folder {folder_name} is already processed (found in cache). Skipping.")
                continue
                
            folder_path = os.path.join(lanna_root, folder_name)
            print(f"\n>>> [LANNA] Processing folder {folder_name} as a single mixed-media native carousel...")
            
            # Gather all media inside this folder
            valid_exts = [".jpg", ".png", ".jpeg", ".mp4", ".mov"]
            media_files = []
            for f in os.listdir(folder_path):
                f_lower = f.lower()
                if any(f_lower.endswith(ext) for ext in valid_exts) and not f.startswith('.') and not f_lower.startswith('vid_') and not f_lower.startswith('thumb_'):
                    media_files.append(os.path.join(folder_path, f))
                    
            if not media_files:
                print(f"  - No valid media files found in {folder_name}. Skipping.")
                continue
                
            # Sort alphabetical to maintain cover/slide order (video first, then images)
            media_files.sort()
            print(f"  - Found {len(media_files)} files in folder {folder_name}: {[os.path.basename(m) for m in media_files]}")
            
            asset_data = []
            has_video = False
            
            for m_file in media_files:
                is_vid = m_file.lower().endswith(('.mp4', '.mov'))
                if is_vid:
                    has_video = True
                
                print(f"  - Uploading {os.path.basename(m_file)} to Supabase...")
                url = upload_to_supabase(m_file, "pulses")
                if url:
                    item = {"url": url}
                    if is_vid:
                        thumb = generate_and_upload_thumbnail(m_file)
                        if thumb:
                            item["thumbnail"] = thumb
                    asset_data.append(item)
                    
            if not asset_data:
                print(f"  - Failed to upload any assets for folder {folder_name}. Skipping.")
                continue
                
            # Generate evocative AI title
            creative_title = generate_creative_title(folder_name)
            cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more mystical updates."
            msg = f"◈ LANNA WHISPERS: {creative_title} ◈{cta}"
            
            print(f"  - Broadcasting carousel with caption: '{msg[:60]}...'")
            success = broadcast_to_buffer(
                text=msg,
                profile_id=BUFFER_PROFILE_ID_LANNA,
                asset_urls=asset_data,
                is_video=has_video,
                post_type="GRID",
                bypass_quota=True
            )
            
            if success:
                print(f"🚀 [LANNA] Carousel for folder {folder_name} successfully added to Buffer!")
                size_cache[cache_key] = str(time.time())
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
                refilled_count += 1
                slots_to_fill -= 1
            else:
                print(f"❌ [LANNA] Failed to broadcast carousel for folder {folder_name} to Buffer.")
                break

    # ----------------------------------------------------
    # 2. INN.OV8 MAIN CHANNEL REPLENISHMENT (1 Reel, 1 Short, 1 Story Daily Variety)
    # ----------------------------------------------------
    print(f"\n>>> Analyzing INN.OV8 Queue...")
    innov8_queue = get_live_scheduled_posts(BUFFER_PROFILE_ID_MAIN)
    print(f">>> INN.OV8 scheduled queue size: {len(innov8_queue)}/10")
    
    if len(innov8_queue) >= 10:
        print(">>> INN.OV8 queue is at maximum capacity (10 posts). Skipping INN.OV8 replenishment.")
    else:
        slots_to_fill = 10 - len(innov8_queue)
        print(f">>> Found {slots_to_fill} available slot(s) in INN.OV8 queue.")
        
        # Helper classification: Classify post type by caption text
        def get_type_of_post(text):
            text_up = text.upper()
            if any(t in text_up for t in ["◈ VAULT GEOLOCATION ◈", "◈ HISTORICAL ARCHIVE ◈", "◈ STREET SCOUT ◈", "GEOLOCATION", "STREET SCOUT"]):
                return "GRID"
            elif any(t in text_up for t in ["◈ STORIES", "STORY"]):
                return "STORY"
            else:
                return "REEL"
                
        # Determine the last scheduled post type in the queue to maintain round-robin rotation
        last_type = "STORY" # default fallback
        if innov8_queue:
            try:
                innov8_queue.sort(key=lambda p: p.get("dueAt", ""))
                last_post = innov8_queue[-1]
                last_type = get_type_of_post(last_post.get("text", ""))
                print(f">>> Last post in queue is classification: {last_type} ('{last_post.get('text', '')[:40]}...')")
            except Exception as e:
                print(f"[CLASSIFICATION ERROR] {e}")
                
        # Rotate order: REEL -> GRID -> STORY
        rotation = ["REEL", "GRID", "STORY"]
        try:
            next_idx = (rotation.index(last_type) + 1) % len(rotation)
        except ValueError:
            next_idx = 0
            
        # Collect available loose assets (ignoring files inside Lanna's numbered directories)
        all_assets = []
        for root, dirs, files in os.walk(SOCIAL_DIR):
            if is_inside_numbered_lanna_folder(root):
                continue
            for f in files:
                if f.lower().endswith(('.mp4', '.mov', '.jpg', '.png')) and not f.startswith('.'):
                    full_path = os.path.join(root, f)
                    try:
                        if os.path.getsize(full_path) < 50 * 1024 * 1024:
                            all_assets.append(full_path)
                    except:
                        pass
                        
        # Sort by mtime (newest first)
        all_assets.sort(key=os.path.getmtime, reverse=True)
        
        # Categorize assets into pools
        pool = {"LANNA": [], "BLUE": [], "LABS": [], "MEMORIES": [], "OTHER": []}
        for asset_path in all_assets:
            category = "OTHER"
            path_up = asset_path.upper()
            if "LANNA" in path_up: category = "LANNA"
            elif "BLUE" in path_up: category = "BLUE"
            elif "LABS" in path_up: category = "LABS"
            elif "MEMORIES" in path_up: category = "MEMORIES"
            pool[category].append(asset_path)
            
        while slots_to_fill > 0:
            target_type = rotation[next_idx]
            print(f"\n>>> [INN.OV8] Attempting to fill slot with type: {target_type}...")
            
            selected_asset = None
            asset_category = None
            vault_location_name = None
            date_str = ""
            
            if target_type == "GRID":
                # GRID: High-Aesthetic Leica Card post from Vault
                if os.path.exists("vault_inventory.json"):
                    try:
                        with open("vault_inventory.json", "r") as f:
                            vault_inventory = json.load(f)
                            
                        # Filter premium aesthetic items
                        valid_vault = []
                        for entry in vault_inventory:
                            thumb = entry.get("thumb_url")
                            score = entry.get("aesthetic_score", 0)
                            tags = entry.get("vision_tags", [])
                            if thumb and thumb.startswith("http") and isinstance(tags, list) and "ERROR" not in tags:
                                try:
                                    if int(score) >= 8:
                                        valid_vault.append(entry)
                                except:
                                    pass
                                    
                        random.shuffle(valid_vault)
                        for entry in valid_vault:
                            vault_key = f"{BUFFER_PROFILE_ID_MAIN}_VAULT_{entry['timestamp']}"
                            if entry["thumb_url"] in size_cache or size_cache.get(entry["thumb_url"]) == vault_key:
                                continue
                            selected_asset = entry
                            asset_category = "VAULT"
                            break
                    except Exception as e:
                        print(f"  - [VAULT ERROR] {e}")
                        
            elif target_type == "REEL":
                # REEL: Vertical Video clips
                candidates = pool["BLUE"] + pool["LABS"] + pool["LANNA"]
                random.shuffle(candidates)
                for candidate in candidates:
                    stat = os.stat(candidate)
                    fingerprint = f"{BUFFER_PROFILE_ID_MAIN}_{stat.st_size}_{stat.st_mtime}"
                    if candidate in size_cache and size_cache[candidate] == fingerprint:
                        continue
                        
                    is_vid = candidate.lower().endswith(('.mp4', '.mov'))
                    if not is_vid:
                        continue
                        
                    # Must be a vertical video
                    width, height = get_video_dimensions(candidate)
                    if height > width:
                        selected_asset = candidate
                        asset_category = "BLUE" if "BLUE" in candidate.upper() else ("LANNA" if "LANNA" in candidate.upper() else "LABS")
                        break
                        
            elif target_type == "STORY":
                # STORY: Vertical images
                candidates = pool["LANNA"] + pool["LABS"] + pool["BLUE"]
                random.shuffle(candidates)
                for candidate in candidates:
                    stat = os.stat(candidate)
                    fingerprint = f"{BUFFER_PROFILE_ID_MAIN}_{stat.st_size}_{stat.st_mtime}"
                    if candidate in size_cache and size_cache[candidate] == fingerprint:
                        continue
                        
                    is_vid = candidate.lower().endswith(('.mp4', '.mov'))
                    if is_vid:
                        continue
                        
                    try:
                        with Image.open(candidate) as img:
                            w, h = img.size
                            if h > w:
                                selected_asset = candidate
                                asset_category = "LANNA" if "LANNA" in candidate.upper() else ("BLUE" if "BLUE" in candidate.upper() else "LABS")
                                break
                    except:
                        pass
                        
            if not selected_asset:
                print(f"  - Could not find any suitable unprocessed assets for type {target_type}. Moving rotation to next index.")
                next_idx = (next_idx + 1) % len(rotation)
                break
                
            is_vid = False
            dispatch_url = None
            social_thumb = None
            
            if asset_category == "VAULT":
                ts = int(selected_asset.get("timestamp", 1777347831))
                date_obj = datetime.datetime.fromtimestamp(ts)
                date_str = date_obj.strftime('%d %b %Y').upper()
                tags_list = selected_asset.get("vision_tags", ["ARCHIVE NODE"])
                tag = tags_list[0] if tags_list else "ARCHIVE NODE"
                coords = selected_asset.get("coords", [18.795, 98.972])
                
                print(f"  - Geocoding Vault coordinates {coords}...")
                city, country = get_place_name(coords[0], coords[1])
                vault_location_name = f"{city}, {country}" if country else city
                
                print(f"  - Generating Leica-styled photo card frame...")
                leica_canvas = create_leica_card(selected_asset["thumb_url"], tag, date_str, coords, location_name=vault_location_name)
                
                if leica_canvas:
                    temp_post_file = f"leica_temp_post_{int(ts)}.jpg"
                    leica_canvas.save(temp_post_file, "JPEG", quality=90)
                    dispatch_url = upload_to_supabase(temp_post_file, "pulses")
                    if os.path.exists(temp_post_file):
                        os.remove(temp_post_file)
                else:
                    dispatch_url = None
            else:
                is_vid = selected_asset.lower().endswith(('.mp4', '.mov'))
                print(f"  - Uploading asset {os.path.basename(selected_asset)} to Supabase...")
                dispatch_url = upload_to_supabase(selected_asset, "pulses")
                if dispatch_url and is_vid:
                    social_thumb = generate_and_upload_thumbnail(selected_asset)
                    
            if not dispatch_url:
                print("  - [INN.OV8] Upload failed, skipping asset.")
                continue
                
            cta = ""
            if asset_category == "LANNA":
                cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more mystical updates."
            elif asset_category == "BLUE":
                cta = "\n\nExperience the full spectrum at bluechromatictriangle.com."
            elif asset_category == "VAULT":
                cta = "\n\nExplore our interactive world map at in-no-v8.world."
            else:
                cta = "\n\nExplore our world at in-no-v8.com or in-no-v8.world."
                
            if asset_category == "VAULT":
                tags_list = selected_asset.get("vision_tags", [])
                formatted_tags = " ".join([f"#{t.lower().replace('_', '')}" for t in tags_list if t])
                loc_split = vault_location_name.split(",")
                city_clean = loc_split[0].strip().replace(" ", "") if loc_split else "ChiangMai"
                city_hashtag = f" #{city_clean}" if city_clean and city_clean != "UnknownLocation" else ""
                
                templates = [
                    f"◈ VAULT GEOLOCATION ◈\n\nStreet Scout snapshot: high-fidelity visual telemetry recorded in {vault_location_name} on {date_str}. Tracing atmospheric textures.{cta} {formatted_tags}{city_hashtag} #StreetScout #VisualArchive",
                    f"◈ HISTORICAL ARCHIVE ◈\n\nRetrieved visual state from our location telemetry index in {vault_location_name} ({date_str}). Composition captured by our autonomous vision sifter.{cta} {formatted_tags}{city_hashtag} #StreetScout #VisualArchive"
                ]
                msg = random.choice(templates)
            else:
                msg = f"◈ {asset_category} BROADCAST ◈\n\n#{os.path.basename(selected_asset).split('_')[0]} workflow snapshot.{cta} #StudioPulse #Innov8Labs"
                
            print(f"  - Broadcasting to INN.OV8 queue (classification {target_type})...")
            success = broadcast_to_buffer(
                text=msg,
                profile_id=BUFFER_PROFILE_ID_MAIN,
                asset_urls=[{"url": dispatch_url, "thumbnail": social_thumb}] if social_thumb else [dispatch_url],
                is_video=is_vid,
                post_type="GRID" if target_type in ["GRID", "STORY"] else "REEL",
                bypass_quota=True,
                location_name=vault_location_name if asset_category == "VAULT" else None
            )
            
            if success:
                print(f"🚀 [INN.OV8] Post successfully added as automatic slot!")
                
                if asset_category == "VAULT":
                    size_cache[selected_asset["thumb_url"]] = f"{BUFFER_PROFILE_ID_MAIN}_VAULT_{selected_asset['timestamp']}"
                else:
                    stat = os.stat(selected_asset)
                    size_cache[selected_asset] = f"{BUFFER_PROFILE_ID_MAIN}_{stat.st_size}_{stat.st_mtime}"
                    
                with open(CACHE_FILE, 'w') as f:
                    json.dump(cache, f)
                    
                refilled_count += 1
                slots_to_fill -= 1
                next_idx = (next_idx + 1) % len(rotation)
            else:
                print(f"❌ [INN.OV8] Failed to broadcast to Buffer.")
                break

    print(f"\n>>> [REFILL] Successfully filled Buffer queues. Replenished total: {refilled_count} posts across all active channels.")

if __name__ == "__main__":
    refill()
