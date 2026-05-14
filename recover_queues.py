import os
import json
import datetime
import sys
import time

# Add current dir to path to import heartbeat functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from heartbeat import broadcast_to_buffer, upload_to_supabase, generate_and_upload_thumbnail, get_video_dimensions, format_video_vertical

SOCIAL_DIR = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL"
PENDING_DIR = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\activity_feed\PENDING_BROADCAST"
CACHE_FILE = "studio_cache.json"
QUOTA_FILE = "buffer_quota.json"

BUFFER_PROFILE_ID_MAIN = os.environ.get("BUFFER_PROFILE_ID")
BUFFER_PROFILE_ID_LANNA = os.environ.get("BUFFER_PROFILE_ID_LANNA")
BUFFER_PROFILE_ID_BLUE = os.environ.get("BUFFER_PROFILE_ID_BLUE")

def recover():
    print(">>> [RECOVERY] Starting queue replenishment for LANNA and BLUE...")
    
    # 1. LANNA RECOVERY (Carousels)
    # lanna_carousel_dir = os.path.join(PENDING_DIR, "CAROUSELS")
    # if os.path.exists(lanna_carousel_dir):
    #     folders = [f for f in os.listdir(lanna_carousel_dir) if os.path.isdir(os.path.join(lanna_carousel_dir, f)) and f != "audio"]
    #     folders.sort() # Process in order
    #     
    #     print(f">>> Found {len(folders)} carousels for LANNA.")
    #     
    #     count = 0
    #     for folder in folders:
    #         if count >= 3: break # Add 3 weeks/slots of content for now
    #         
    #         folder_path = os.path.join(lanna_carousel_dir, folder)
    #         valid_exts = [".jpg", ".png", ".mp4", ".mov"]
    #         media_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in valid_exts]
    #         
    #         if not media_files: continue
    #         
    #         print(f">>> [LANNA] Processing Carousel {folder} ({len(media_files)} items)...")
    #         
    #         asset_urls = []
    #         for m in media_files:
    #             url = upload_to_supabase(m)
    #             if url:
    #                 if m.lower().endswith(('.mp4', '.mov')):
    #                     thumb = generate_and_upload_thumbnail(m)
    #                     asset_urls.append({"url": url, "thumbnail": thumb})
    #                 else:
    #                     asset_urls.append(url)
    #         
    #         if asset_urls:
    #             msg = f"◈ LANNA WHISPERS ◈\n\nChapter {folder}: Atmospheric synthesis in progress. #LannaWhispers #StudioPulse #Innov8Labs"
    #             success = broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_LANNA, asset_urls=asset_urls, is_video=False, post_type="GRID", bypass_quota=True)
    #             if success:
    #                 count += 1
    #                 # Move folder to a "PROCESSED" or just delete? User might want to keep them.
    #                 # For now, I'll just mark it in cache or something.
    #                 pass
    
    # 2. BLUE RECOVERY (Silas)
    blue_silas_dir = os.path.join(SOCIAL_DIR, "BLUE", "SILAS")
    if os.path.exists(blue_silas_dir):
        files = [f for f in os.listdir(blue_silas_dir) if f.lower().endswith(('.mp4', '.mov', '.jpg', '.png'))]
        files.sort(reverse=True) # Newest first? Or alphabetically
        
        print(f">>> Found {len(files)} assets for BLUE/SILAS.")
        
        count = 0
        for f in files:
            if count >= 4: break # Fill 4 slots
            
            file_path = os.path.join(blue_silas_dir, f)
            is_vid = f.lower().endswith(('.mp4', '.mov'))
            
            print(f">>> [BLUE] Processing {f}...")
            
            # For Blue, let's stick to REELS for videos and GRID for images
            width, height = get_video_dimensions(file_path)
            is_vert = height > width
            q_type = ("REEL" if is_vid else "STORY") if is_vert else "GRID"
            
            # YouTube conversion for images
            current_asset_path = file_path
            if not is_vid:
                print(f">>> [BLUE] Converting image to video for YouTube: {f}")
                from heartbeat import convert_image_to_video
                vid_path = convert_image_to_video(file_path)
                if vid_path:
                    current_asset_path = vid_path
                    is_vid = True
                    q_type = "REEL" # Treat as Reel/Short
            
            # If it's a video and not vertical, format it
            dispatch_url = upload_to_supabase(current_asset_path)
            social_thumb = None
            if is_vid:
                if not is_vert:
                    formatted = format_video_vertical(current_asset_path)
                    if formatted != current_asset_path:
                        dispatch_url = upload_to_supabase(formatted, "formatted")
                        os.remove(formatted)
                social_thumb = generate_and_upload_thumbnail(current_asset_path)
            
            msg = f"◈ BLUE SPECTRUM ◈\n\nSilas Chronicles: {f.split('.')[0]}. #Silas #BlueSpectrum #StudioPulse #Innov8Labs"
            success = broadcast_to_buffer(msg, profile_id=BUFFER_PROFILE_ID_BLUE, asset_urls=[{"url": dispatch_url, "thumbnail": social_thumb}] if social_thumb else [dispatch_url], is_video=is_vid, post_type=q_type, bypass_quota=True)
            
            # Cleanup temp video if it was converted from image
            if current_asset_path != file_path and os.path.exists(current_asset_path):
                os.remove(current_asset_path)
                
            if success:
                count += 1

if __name__ == "__main__":
    recover()
