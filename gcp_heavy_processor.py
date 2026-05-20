#!/usr/bin/env python
"""
GCP Heavy Parallel AI Batch Processor
=====================================
A high-throughput, concurrent, multithreaded batch processing pipeline that
connects to your Google Cloud Vertex AI project (studio-pulse-vault) and harnesses
Gemini 2.5 Flash to analyze massive directories of images, videos, and audio.

Supports Dual Authentication:
- GCP Terminal Mode (Cloud Shell / VM): Uses standard Application Default Credentials (ADC).
- Local Mode (Windows PC): Automatically falls back to token_drive.json.

Includes advanced features:
- Concurrency via ThreadPoolExecutor.
- Exponential backoff rate limit retry protection (handling HTTP 429 / 503).
- Structured JSON outputs and metadata mapping.
- Live progress console dashboard with token estimation and billing tracking.
"""

import os
import sys
import time
import json
import base64
import requests
import argparse
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Optional: Try to import Pillow for basic metadata checks
try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

# Thread safety locks
console_lock = Lock()
file_write_lock = Lock()

# Stats tracker
stats = {
    "total_files": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "images_processed": 0,
    "videos_processed": 0,
    "audios_processed": 0,
    "estimated_input_tokens": 0,
    "estimated_output_tokens": 0,
    "retry_count": 0,
}

# Pricing for gemini-2.5-flash: $0.075 / 1M input tokens, $0.30 / 1M output tokens
PRICE_PER_INPUT_TOKEN = 0.075 / 1000000
PRICE_PER_OUTPUT_TOKEN = 0.30 / 1000000


def get_gcp_token():
    """
    Resolves the GCP access token.
    Mode 1: Try local token_drive.json first if it exists - for local Windows PC.
    Mode 2: Fallback to Google Application Default Credentials (ADC) - for GCP VM / Cloud Shell.
    """
    token_file = 'token_drive.json'
    client_secret_file = 'client_secret.json'
    project_id = 'studio-pulse-vault'
    
    # Try to load project_id from client_secret.json
    if os.path.exists(client_secret_file):
        try:
            with open(client_secret_file, 'r') as f:
                cs = json.load(f)
                project_id = cs.get("installed", {}).get("project_id", project_id)
        except Exception:
            pass

    # Try local token_drive.json
    if os.path.exists(token_file):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as OAuthRequest
            creds = Credentials.from_authorized_user_file(token_file)
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(OAuthRequest())
                    with open(token_file, 'w') as f:
                        f.write(creds.to_json())
            if creds and creds.token:
                return creds.token, project_id
        except Exception as e:
            with console_lock:
                print(f"[AUTH WARNING] Failed to read token_drive.json locally: {e}")

    # Fallback to Application Default Credentials (GCP Terminals / Cloud Shell)
    try:
        import google.auth
        from google.auth.transport.requests import Request as GoogleRequest
        creds, project = google.auth.default()
        creds.refresh(GoogleRequest())
        if creds and creds.token:
            return creds.token, project or "studio-pulse-vault"
    except Exception:
        pass
                
    return None, project_id


def estimate_tokens(text):
    """Simple heuristic token estimation (4 characters ~= 1 token)."""
    if not text:
        return 0
    return max(1, len(str(text)) // 4)


def call_gemini_with_backoff(
    prompt,
    system_instruction=None,
    image_data=None,
    audio_data=None,
    image_mime="image/jpeg",
    audio_mime="audio/mp3",
    response_json=False,
    model="gemini-2.5-flash",
    max_retries=5,
    initial_delay=2.0
):
    """
    Calls the Vertex AI Gemini REST API with exponential backoff on HTTP 429 / 503.
    """
    token, project_id = get_gcp_token()
    if not token:
        raise Exception("GCP Authentication token could not be resolved. Please run setup_gcp_credentials.py or run 'gcloud auth application-default login' in your terminal.")

    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model}:generateContent"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    parts = []

    # 1. Base64 Image
    if image_data:
        b64_str = image_data if isinstance(image_data, str) else base64.b64encode(image_data).decode('utf-8')
        parts.append({
            "inlineData": {
                "mimeType": image_mime,
                "data": b64_str
            }
        })
        # Estimate image tokens (approx 258 tokens for standard resizing in Gemini)
        stats["estimated_input_tokens"] += 258

    # 2. Base64 Audio
    if audio_data:
        b64_str = audio_data if isinstance(audio_data, str) else base64.b64encode(audio_data).decode('utf-8')
        parts.append({
            "inlineData": {
                "mimeType": audio_mime,
                "data": b64_str
            }
        })
        # Estimate audio tokens (approx 100 tokens per minute of audio)
        stats["estimated_input_tokens"] += 500

    # 3. Prompt Text
    parts.append({"text": prompt})
    stats["estimated_input_tokens"] += estimate_tokens(prompt)

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ]
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        stats["estimated_input_tokens"] += estimate_tokens(system_instruction)

    generation_config = {}
    if response_json:
        generation_config["responseMimeType"] = "application/json"
    if generation_config:
        payload["generationConfig"] = generation_config

    delay = initial_delay
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                resp_data = response.json()
                text_content = resp_data['candidates'][0]['content']['parts'][0]['text']
                stats["estimated_output_tokens"] += estimate_tokens(text_content)
                return text_content
            
            elif response.status_code in [429, 503]:
                stats["retry_count"] += 1
                with console_lock:
                    print(f"\n[RATE LIMIT / OVERLOAD] HTTP {response.status_code}. Retrying in {delay:.1f}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2.0
            
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as req_err:
            if attempt == max_retries - 1:
                raise req_err
            time.sleep(delay)
            delay *= 2.0

    raise Exception("Exceeded maximum retries due to persistent rate limiting or service unavailability.")


def process_image(file_path):
    """Extracts aesthetic tags, visual descriptions, and creative title using Gemini."""
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    # Determine standard extension
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = "image/jpeg"
    if ext == ".png":
        mime_type = "image/png"
    elif ext == ".webp":
        mime_type = "image/webp"

    system_instruction = (
        "You are an expert studio content archivist. You analyze photos and output detailed metadata "
        "in structured JSON format containing exactly four keys: 'creative_title', 'description', "
        "'tags' (a list of 5-8 relevant visual/technical terms), and 'safety_status' ('safe' or 'flagged')."
    )
    prompt = (
        f"Analyze this image. Filename is: '{os.path.basename(file_path)}'. Create an evocative professional studio title, "
        "a 10-word studio-grade description, and 5-8 descriptive tags."
    )

    response_text = call_gemini_with_backoff(
        prompt=prompt,
        system_instruction=system_instruction,
        image_data=image_bytes,
        image_mime=mime_type,
        response_json=True
    )

    metadata = json.loads(response_text)
    stats["images_processed"] += 1
    return metadata


def process_video(file_path):
    """Uses ffmpeg to grab a frame, then passes it to Gemini for video description."""
    # Capture middle frame
    temp_frame = f"temp_frame_{int(time.time())}_{os.path.basename(file_path).replace(' ', '_')}.jpg"
    try:
        cmd = [
            'ffmpeg', '-y', '-i', file_path, '-ss', '00:00:02', 
            '-vframes', '1', '-f', 'image2', temp_frame
        ]
        # Run ffmpeg silently
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        
        with open(temp_frame, "rb") as f:
            frame_bytes = f.read()

        system_instruction = (
            "You are a professional film editor and archivist. You analyze video frames and output detailed metadata "
            "in structured JSON format containing: 'creative_title', 'description' (describing the visual scene as a motion asset), "
            "'tags' (5-8 industry-standard video production/mood tags), and 'safety_status'."
        )
        prompt = (
            f"This is a preview frame from the video file: '{os.path.basename(file_path)}'. Generate the creative title, "
            "visual scene description, and 5-8 production/mood tags."
        )

        response_text = call_gemini_with_backoff(
            prompt=prompt,
            system_instruction=system_instruction,
            image_data=frame_bytes,
            image_mime="image/jpeg",
            response_json=True
        )
        
        metadata = json.loads(response_text)
        metadata["media_type"] = "video"
        stats["videos_processed"] += 1
        return metadata

    finally:
        if os.path.exists(temp_frame):
            try:
                os.remove(temp_frame)
            except Exception:
                pass


def process_audio(file_path):
    """Transcribes or generates descriptive audio summaries natively via Gemini."""
    # Gemini handles audio files up to 20MB directly in generateContent REST API
    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    ext = os.path.splitext(file_path)[1].lower()
    mime_type = "audio/mp3"
    if ext == ".wav":
        mime_type = "audio/wav"
    elif ext == ".m4a" or ext == ".mp4":
        mime_type = "audio/mp4"

    system_instruction = (
        "You are an expert audio engineer and musical transcriber. You analyze audio tracks and output metadata "
        "in structured JSON format containing: 'creative_title' (fitting the song/speech style), "
        "'summary' (a detailed paragraph summarizing the vocals, instruments, and mood), and 'transcription' "
        "(raw SubRip (SRT) lyrical subtitle transcript format or standard spoken text)."
    )
    prompt = (
        f"Analyze this audio file: '{os.path.basename(file_path)}'. Transcribe speech/vocals into SRT transcript format "
        "and summarize the instrumentation and aesthetic style."
    )

    response_text = call_gemini_with_backoff(
        prompt=prompt,
        system_instruction=system_instruction,
        audio_data=audio_bytes,
        audio_mime=mime_type,
        response_json=True
    )

    metadata = json.loads(response_text)
    metadata["media_type"] = "audio"
    stats["audios_processed"] += 1
    return metadata


def process_single_file(file_path):
    """Dispatcher for individual files based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    base_name = os.path.basename(file_path)
    
    start_time = time.time()
    try:
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            meta = process_image(file_path)
            meta["media_type"] = "image"
        elif ext in ['.mp4', '.mov', '.mkv']:
            meta = process_video(file_path)
            meta["media_type"] = "video"
        elif ext in ['.mp3', '.wav', '.m4a']:
            meta = process_audio(file_path)
            meta["media_type"] = "audio"
        else:
            raise Exception(f"Unsupported extension: {ext}")
            
        elapsed = time.time() - start_time
        meta["original_filename"] = base_name
        meta["file_path"] = os.path.abspath(file_path)
        meta["file_size_bytes"] = os.path.getsize(file_path)
        meta["processed_at"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        meta["duration_seconds"] = round(elapsed, 2)
        
        with console_lock:
            stats["success"] += 1
            stats["processed"] += 1
            # Beautiful print update
            pct = (stats["processed"] / stats["total_files"]) * 100
            print(f"[{pct:6.2f}%] SUCCESS: {base_name} ({elapsed:.2f}s)")
            
        return meta

    except Exception as e:
        elapsed = time.time() - start_time
        with console_lock:
            stats["failed"] += 1
            stats["processed"] += 1
            pct = (stats["processed"] / stats["total_files"]) * 100
            print(f"[{pct:6.2f}%] FAILED : {base_name} ({elapsed:.2f}s) - {str(e)}")
            
        return {
            "original_filename": base_name,
            "file_path": os.path.abspath(file_path),
            "media_type": "unknown",
            "error": str(e),
            "processed_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "duration_seconds": round(elapsed, 2)
        }


def scan_directory(directory_path):
    """Scans the folder recursively for compatible media assets."""
    supported_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.mkv', '.mp3', '.wav', '.m4a'}
    files_to_process = []
    
    for root, dirs, files in os.walk(directory_path):
        # Ignore common system / cache folders
        dirs[:] = [d for dirs_list in [dirs] for d in dirs_list if d not in [
            'node_modules', '.git', '.vercel', 'activity_feed', 'RECYCLE.BIN', 'Auto-Save'
        ]]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_exts:
                files_to_process.append(os.path.join(root, file))
                
    return files_to_process


def main():
    parser = argparse.ArgumentParser(description="GCP Parallel AI Batch Processor using Gemini via Vertex AI")
    parser.add_argument("directory", nargs="?", default=".", help="Directory containing images, videos, or audio (default: current folder)")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent execution threads (default: 5)")
    parser.add_argument("--output", default="vault_batch_catalog.json", help="Output catalog filename (default: vault_batch_catalog.json)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of processed files (default: all)")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.directory)
    print("=====================================================================")
    print("       INITIALIZING GCP HEAVY AI BATCH PARALLEL PROCESSOR            ")
    print("=====================================================================")
    print(f"Target Directory : {target_dir}")
    print(f"Concurrency Limit: {args.workers} threads")
    print(f"Output Catalog   : {args.output}")

    # Verify GCP configuration / token validity
    print("\n[AUTH] Loading Google Cloud Credentials...")
    token, proj_id = get_gcp_token()
    if not token:
        print("[CRITICAL ERROR] GCP Authentication failed! Please run 'python setup_gcp_credentials.py' or check your GCP settings.")
        sys.exit(1)
    print(f"[AUTH SUCCESS] Connected to Project: '{proj_id}'")

    # Scan directory
    print("\n[DISCOVERY] Scanning directory...")
    all_files = scan_directory(target_dir)
    stats["total_files"] = len(all_files) if args.limit <= 0 else min(args.limit, len(all_files))
    
    if stats["total_files"] == 0:
        print("No compatible media files found. Supported: Images, Videos, Audios.")
        sys.exit(0)
        
    print(f"Found {len(all_files)} compatible files. Processing {stats['total_files']} files...")
    files_to_process = all_files[:stats["total_files"]]

    start_time = time.time()
    results = []

    # Run Parallel Execution using ThreadPoolExecutor
    print("\n[EXECUTION] Launching Multithreaded Pipeline...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_single_file, f): f for f in files_to_process}
        
        for future in as_completed(futures):
            results.append(future.result())

    # Finalize stats
    total_elapsed = time.time() - start_time
    total_cost = (stats["estimated_input_tokens"] * PRICE_PER_INPUT_TOKEN) + (stats["estimated_output_tokens"] * PRICE_PER_OUTPUT_TOKEN)

    # Save results
    output_path = os.path.abspath(args.output)
    catalog_data = {
        "batch_metadata": {
            "target_directory": target_dir,
            "total_files_discovered": len(all_files),
            "files_processed": stats["processed"],
            "success_count": stats["success"],
            "failed_count": stats["failed"],
            "total_duration_seconds": round(total_elapsed, 2),
            "estimated_cost_usd": round(total_cost, 5),
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        },
        "statistics": stats,
        "assets": results
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)

    print("\n=====================================================================")
    print("                      BATCH PROCESSING COMPLETE                      ")
    print("=====================================================================")
    print(f"Total Processed       : {stats['processed']} files")
    print(f" -> SUCCESS           : {stats['success']}")
    print(f" -> FAILED            : {stats['failed']}")
    print(f"Image Assets          : {stats['images_processed']}")
    print(f"Video Assets          : {stats['videos_processed']}")
    print(f"Audio Assets          : {stats['audios_processed']}")
    print(f"Exponential Retries   : {stats['retry_count']}")
    print(f"Input Token Est.      : {stats['estimated_input_tokens']}")
    print(f"Output Token Est.     : {stats['estimated_output_tokens']}")
    print(f"Estimated Cost (GCP)  : ${total_cost:.5f} USD (Harnessed GCP Credits)")
    print(f"Total Execution Time  : {total_elapsed/60:.2f} minutes ({total_elapsed:.2f}s)")
    print(f"Unified Catalog Saved : {output_path}")
    print("=====================================================================")


if __name__ == "__main__":
    main()
