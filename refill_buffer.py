import os
import json
import datetime
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

from heartbeat import broadcast_to_buffer, upload_to_supabase, generate_and_upload_thumbnail, get_video_dimensions, format_video_vertical

SOCIAL_DIR = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL"
CACHE_FILE = "studio_cache.json"
QUOTA_FILE = "buffer_quota.json"

BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")

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
        
        draw.text((right_x - logo_w, footer_y), logo_text, fill="black", font=font_bold)
        draw.text((right_x - exif_w, footer_y + 35), exif_text, fill="#666666", font=font_reg)
        
        # Separator line
        draw.line([margin, footer_y - 15, right_x, footer_y - 15], fill="#EAEAEA", width=1)
        
        return canvas
    except Exception as e:
        print(f"[LEICA CARD GENERATION ERROR] {e}")
        return None

def refill():
    print(">>> [REFILL] Starting manual Buffer replenishment...")
    
    # Load Cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f: cache = json.load(f)
    
    # Load Quota
    quota = {}
    if os.path.exists(QUOTA_FILE):
        with open(QUOTA_FILE, 'r') as f: quota = json.load(f)
    
    current_week = datetime.datetime.now().strftime('%Y-%W')
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Target Profiles
    profiles = [
        {"id": BUFFER_PROFILE_ID_MAIN, "label": "INN.OV8", "folder": "INNOV8"},
        {"id": BUFFER_PROFILE_ID_LANNA, "label": "LANNA", "folder": "LANNA"},
        {"id": BUFFER_PROFILE_ID_BLUE, "label": "BLUE", "folder": "BLUE"}
    ]
    
    # Collect available assets from SOCIAL recursively
    all_assets = []
    for root, dirs, files in os.walk(SOCIAL_DIR):
        for f in files:
            if f.lower().endswith(('.mp4', '.mov', '.jpg', '.png')) and not f.startswith('.'):
                full_path = os.path.join(root, f)
                try:
                    # Enforce a 50MB file size limit to prevent uploading massive files to Supabase/Buffer
                    if os.path.getsize(full_path) < 50 * 1024 * 1024:
                        all_assets.append(full_path)
                except:
                    pass
    
    # Sort by mtime (newest first)
    all_assets.sort(key=os.path.getmtime, reverse=True)
    
    print(f">>> Found {len(all_assets)} potential assets in SOCIAL.")
    
    # Collect all assets and categorize them
    pool = {"LANNA": [], "BLUE": [], "LABS": [], "MEMORIES": [], "OTHER": []}
    for asset_path in all_assets:
        category = "OTHER"
        path_up = asset_path.upper()
        if "LANNA" in path_up: category = "LANNA"
        elif "BLUE" in path_up: category = "BLUE"
        elif "LABS" in path_up: category = "LABS"
        elif "MEMORIES" in path_up: category = "MEMORIES"
        pool[category].append(asset_path)

    # REFILL LOGIC: 1 post per project per day for INN.OV8 variety
    refilled_count = 0
    
    # We'll try to fill slots for all profiles
    for profile in profiles:
        day_after_tomorrow = (datetime.datetime.now() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        target_dates = [today, tomorrow, day_after_tomorrow]
        for target_date in target_dates:
            # Check current total queue depth for this profile and date
            daily_stats = quota.get(target_date, {}).get(profile["id"], {})
            current_total = daily_stats.get("total", 0)
            
            # Limit: 3 per day for MAIN, 1-2 for others
            if current_total >= (3 if profile["id"] == BUFFER_PROFILE_ID_MAIN else 1):
                continue
                
            # SELECT ASSET
            selected_asset = None
            asset_category = None
            vault_location_name = None
            
            if profile["id"] == BUFFER_PROFILE_ID_MAIN:
                # MASTER CHANNEL: Pick from all pools, but only 1 per category per day
                categories = ["LANNA", "BLUE", "LABS", "MEMORIES", "VAULT"]
                random.shuffle(categories)
                
                for cat in categories:
                    # Check if this category was already used TODAY for MAIN
                    if daily_stats.get(f"cat_{cat}", 0) >= 1:
                        continue
                    
                    if cat == "MEMORIES":
                        # Enforce weekly memories cooldown
                        if quota.get("weekly_memory_sent") == current_week:
                            continue
                    
                    if cat == "VAULT":
                        # Pick from vault inventory
                        if os.path.exists("vault_inventory.json"):
                            try:
                                with open("vault_inventory.json", "r") as f:
                                    vault_inventory = json.load(f)
                                
                                # Filter high-aesthetic items
                                valid_vault = []
                                for entry in vault_inventory:
                                    thumb = entry.get("thumb_url")
                                    tags = entry.get("vision_tags", [])
                                    score = entry.get("aesthetic_score", 0)
                                    if thumb and thumb.startswith("http") and isinstance(tags, list) and "ERROR" not in tags:
                                        try:
                                            if int(score) >= 8:
                                                valid_vault.append(entry)
                                        except:
                                            pass
                                
                                random.shuffle(valid_vault)
                                for entry in valid_vault:
                                    # Unique fingerprint: check if already in cache
                                    fingerprint = f"{profile['id']}_VAULT_{entry['timestamp']}"
                                    if entry["thumb_url"] in cache or cache.get(entry["thumb_url"]) == fingerprint:
                                        continue
                                    
                                    selected_asset = entry
                                    asset_category = "VAULT"
                                    break
                            except Exception as e:
                                print(f"[VAULT LOAD ERROR] {e}")
                    else:
                        # Try to find an asset from this category in folder pools
                        cat_pool = pool.get(cat, [])
                        random.shuffle(cat_pool)
                        for candidate in cat_pool:
                            stat = os.stat(candidate)
                            fingerprint = f"{profile['id']}_{stat.st_size}_{stat.st_mtime}"
                            if candidate in cache and cache[candidate] == fingerprint:
                                continue
                            
                            selected_asset = candidate
                            asset_category = cat
                            break
                    
                    if selected_asset:
                        break
            else:
                # SPECIALIZED CHANNEL: Pick only from its own pool
                asset_category = profile["label"]
                for candidate in pool.get(asset_category, []):
                    stat = os.stat(candidate)
                    fingerprint = f"{profile['id']}_{stat.st_size}_{stat.st_mtime}"
                    if candidate in cache and cache[candidate] == fingerprint:
                        continue
                    selected_asset = candidate
                    break
            
            if not selected_asset:
                continue

            # Determine Type and Orientation
            if asset_category == "VAULT":
                is_vid = False
                is_vert = True # Assume vertical/grid format for high aesthetic photographs
                q_type = "GRID"
                
                # Fetch details for Leica card frame
                ts = int(selected_asset.get("timestamp", 1777347831))
                date_obj = datetime.datetime.fromtimestamp(ts)
                date_str = date_obj.strftime('%d %b %Y').upper()
                tags_list = selected_asset.get("vision_tags", ["ARCHIVE NODE"])
                tag = tags_list[0] if tags_list else "ARCHIVE NODE"
                coords = selected_asset.get("coords", [18.795, 98.972])
                
                # Reverse geocode GPS coordinates
                print(f">>> [REFILL] Geocoding coordinates {coords}...")
                city, country = get_place_name(coords[0], coords[1])
                vault_location_name = f"{city}, {country}" if country else city
                print(f">>> [REFILL] Geocode result: {vault_location_name}")
                
                print(f">>> [REFILL] Generating Leica-styled card frame for Vault Image {selected_asset.get('filename')}...")
                
                # Compose framed photo card
                leica_canvas = create_leica_card(selected_asset["thumb_url"], tag, date_str, coords, location_name=vault_location_name)
                
                if leica_canvas:
                    temp_post_file = f"leica_temp_post_{int(ts)}.jpg"
                    leica_canvas.save(temp_post_file, "JPEG", quality=90)
                    
                    # Upload the generated framed image to Supabase
                    dispatch_url = upload_to_supabase(temp_post_file)
                    
                    # Clean up
                    if os.path.exists(temp_post_file):
                        os.remove(temp_post_file)
                else:
                    dispatch_url = None
                
                if not dispatch_url:
                    print(">>> [REFILL] Leica card generation/upload failed, skipping.")
                    continue
                
                social_thumb = None
                print(f">>> [REFILL] Leica Frame complete. Public url: {dispatch_url}")
            else:
                is_vid = selected_asset.lower().endswith(('.mp4', '.mov'))
                width, height = get_video_dimensions(selected_asset)
                is_vert = height > width
                is_strict_vertical_video = is_vid and width == 1080 and height == 1920
                q_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
                
                # YouTube Final Check
                if profile["id"] == BUFFER_PROFILE_ID_BLUE and not is_strict_vertical_video:
                    continue

                print(f">>> [REFILL] Variety Routing: Pushing {os.path.basename(selected_asset)} ({asset_category}) to {profile['label']} for {target_date}")
                
                # Format and Upload
                dispatch_url = upload_to_supabase(selected_asset)
                if not dispatch_url:
                    continue
                social_thumb = generate_and_upload_thumbnail(selected_asset) if is_vid else None

            # CAPTION LOGIC (CTAs)
            cta = ""
            if asset_category == "LANNA":
                cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more mystical updates."
            elif asset_category == "BLUE":
                cta = "\n\nExperience the full spectrum at bluechromatictriangle.com."
            elif asset_category == "VAULT":
                cta = "\n\nExplore our interactive world map at in-no-v8.world."
            else:
                cta = "\n\nExplore our world at in-no-v8.com or in-no-v8.world."

            # Construct Message
            if asset_category == "VAULT":
                coords = selected_asset.get("coords", [0.0, 0.0])
                lat_str = f"{coords[0]:.5f}" if coords else "18.795"
                lng_str = f"{coords[1]:.5f}" if coords else "98.972"
                tags_list = selected_asset.get("vision_tags", [])
                
                # City Tag
                loc_split = vault_location_name.split(",")
                city_clean = loc_split[0].strip().replace(" ", "") if loc_split else "ChiangMai"
                city_hashtag = f" #{city_clean}" if city_clean and city_clean != "UnknownLocation" else ""
                
                formatted_tags = " ".join([f"#{t.lower().replace('_', '')}" for t in tags_list if t])
                
                templates = [
                    f"◈ VAULT GEOLOCATION ◈\n\nStreet Scout snapshot: high-fidelity visual telemetry recorded in {vault_location_name} on {date_str}. Tracing atmospheric textures.{cta} {formatted_tags}{city_hashtag} #StreetScout #VisualArchive",
                    f"◈ HISTORICAL ARCHIVE ◈\n\nRetrieved visual state from our location telemetry index in {vault_location_name} ({date_str}). Composition captured by our autonomous vision sifter.{cta} {formatted_tags}{city_hashtag} #StreetScout #VisualArchive",
                    f"◈ STREET SCOUT ◈\n\nIngesting a raw visual fragment into the studio portal. Location: {vault_location_name}. Captured: {date_str}. High-aesthetic street study.{cta} {formatted_tags}{city_hashtag} #StreetScout #VisualArchive"
                ]
                msg = random.choice(templates)
            else:
                msg = f"◈ {asset_category} BROADCAST ◈\n\n#{os.path.basename(selected_asset).split('_')[0]} workflow snapshot.{cta} #StudioPulse #Innov8Labs"
            
            # Broadcast with dynamic location name
            success = broadcast_to_buffer(
                msg, 
                profile_id=profile["id"], 
                asset_urls=[{"url": dispatch_url, "thumbnail": social_thumb}] if social_thumb else [dispatch_url], 
                is_video=is_vid, 
                post_type=q_type, 
                bypass_quota=True,
                location_name=vault_location_name
            )
            
            if success:
                # Update Quota
                if target_date not in quota: quota[target_date] = {}
                if profile["id"] not in quota[target_date]: quota[target_date][profile["id"]] = {}
                quota[target_date][profile["id"]][q_type] = quota[target_date][profile["id"]].get(q_type, 0) + 1
                quota[target_date][profile["id"]]["total"] = quota[target_date][profile["id"]].get("total", 0) + 1
                if asset_category:
                    quota[target_date][profile["id"]][f"cat_{asset_category}"] = quota[target_date][profile["id"]].get(f"cat_{asset_category}", 0) + 1
                
                if asset_category == "MEMORIES":
                    quota["weekly_memory_sent"] = current_week
                
                # Update Cache
                if asset_category == "VAULT":
                    cache[selected_asset["thumb_url"]] = f"{profile['id']}_VAULT_{selected_asset['timestamp']}"
                else:
                    stat = os.stat(selected_asset)
                    cache[selected_asset] = f"{profile['id']}_{stat.st_size}_{stat.st_mtime}"
                
                refilled_count += 1
                
                with open(QUOTA_FILE, 'w') as f: json.dump(quota, f)
                with open(CACHE_FILE, 'w') as f: json.dump(cache, f)

    print(f">>> [REFILL] Successfully added {refilled_count} items to Buffer queues.")

if __name__ == "__main__":
    refill()
