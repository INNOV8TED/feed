import os
import json
import datetime
import sys

# Add current dir to path to import heartbeat functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from heartbeat import broadcast_to_buffer, upload_to_supabase, generate_and_upload_thumbnail, get_video_dimensions, format_video_vertical

SOCIAL_DIR = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL"
CACHE_FILE = "studio_cache.json"
QUOTA_FILE = "buffer_quota.json"

BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")

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
                all_assets.append(os.path.join(root, f))
    
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
        target_dates = [today, tomorrow]
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
            
            if profile["id"] == BUFFER_PROFILE_ID_MAIN:
                # MASTER CHANNEL: Pick from all pools, but only 1 per category per day
                categories = ["LANNA", "BLUE", "LABS", "MEMORIES"]
                import random
                random.shuffle(categories)
                
                for cat in categories:
                    # Check if this category was already used TODAY for MAIN
                    if daily_stats.get(f"cat_{cat}", 0) >= 1:
                        continue
                    
                    # Try to find an asset from this category
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
                    
                    if selected_asset: break
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
            
            if not selected_asset: continue

            # Determine Type and Orientation
            is_vid = selected_asset.lower().endswith(('.mp4', '.mov'))
            width, height = get_video_dimensions(selected_asset)
            is_vert = height > width
            is_strict_vertical_video = is_vid and width == 1080 and height == 1920
            q_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
            
            # YouTube Final Check
            if profile["id"] == BUFFER_PROFILE_ID_BLUE and not is_strict_vertical_video:
                continue

            print(f">>> [REFILL] Variety Routing: Pushing {os.path.basename(selected_asset)} ({asset_category}) to {profile['label']} for {target_date}")
            
            # CAPTION LOGIC (CTAs)
            cta = ""
            if asset_category == "LANNA":
                cta = "\n\nFollow @lanna.whispers or visit lannawhispers.com for more mystical updates."
            elif asset_category == "BLUE":
                cta = "\n\nExperience the full spectrum at bluechromatictriangle.com."
            else:
                cta = "\n\nExplore our world at in-no-v8.com or in-no-v8.world."

            msg = f"◈ {asset_category} BROADCAST ◈\n\n#{os.path.basename(selected_asset).split('_')[0]} workflow snapshot.{cta} #StudioPulse #Innov8Labs"
            
            # Format and Upload
            dispatch_url = upload_to_supabase(selected_asset)
            if not dispatch_url: continue
            social_thumb = generate_and_upload_thumbnail(selected_asset) if is_vid else None
            
            # Broadcast
            success = broadcast_to_buffer(msg, profile_id=profile["id"], asset_urls=[{"url": dispatch_url, "thumbnail": social_thumb}] if social_thumb else [dispatch_url], is_video=is_vid, post_type=q_type, bypass_quota=True)
            
            if success:
                # Update Quota
                if target_date not in quota: quota[target_date] = {}
                if profile["id"] not in quota[target_date]: quota[target_date][profile["id"]] = {}
                quota[target_date][profile["id"]][q_type] = quota[target_date][profile["id"]].get(q_type, 0) + 1
                quota[target_date][profile["id"]]["total"] = quota[target_date][profile["id"]].get("total", 0) + 1
                if asset_category:
                    quota[target_date][profile["id"]][f"cat_{asset_category}"] = quota[target_date][profile["id"]].get(f"cat_{asset_category}", 0) + 1
                
                # Update Cache
                stat = os.stat(selected_asset)
                cache[selected_asset] = f"{profile['id']}_{stat.st_size}_{stat.st_mtime}"
                refilled_count += 1
                
                with open(QUOTA_FILE, 'w') as f: json.dump(quota, f)
                with open(CACHE_FILE, 'w') as f: json.dump(cache, f)
    print(f">>> [REFILL] Successfully added {refilled_count} items to Buffer queues.")

if __name__ == "__main__":
    refill()
