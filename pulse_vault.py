import os
import json
import io
import requests
import base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from supabase import create_client
from gcp_gemini_client import call_gemini
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = 'token_drive.json'
VAULT_FOLDER_ID = '19TGeenMYf6gMqg_KiXHr6Mvjh9edgv5k'

# Initialize Clients
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def get_google_creds():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_image_base64(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return base64.b64encode(fh.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def analyze_image_with_ai(base64_image):
    """Uses Google Cloud Vertex AI Gemini to determine safety and generate a story."""
    try:
        system_prompt = (
            "Analyze this photo for a professional studio activity feed. \n"
            "1. Is it safe to publish? (No recognizable people, no private domestic scenes like kitchens/bedrooms, no sensitive content).\n"
            "2. Does it look like studio equipment, a render, abstract art, or a workspace?\n"
            "3. If safe, generate a professional, atmospheric caption (1-2 sentences) about the creative process or the 'studio mood'.\n"
            "4. Provide a 'Studio Aesthetic' score from 1-10.\n\n"
            "Return JSON matching this exact schema: {\"safe\": bool, \"caption\": \"string\", \"score\": int}"
        )
        response_text = call_gemini(
            prompt="Analyze this image and return the JSON safety analysis.",
            system_instruction=system_prompt,
            image_data=base64_image,
            response_json=True
        )
        if response_text:
            return json.loads(response_text)
        return None
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def find_all_images_in_folder(service, folder_id):
    """Recursively finds all images in the given folder and subfolders."""
    images = []
    
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, fields="nextPageToken, files(id, name, mimeType, thumbnailLink, createdTime)").execute()
    items = results.get('files', [])
    
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            images.extend(find_all_images_in_folder(service, item['id']))
        elif item['mimeType'].startswith('image/'):
            images.append(item)
            
    return images

def scan_drive_vault(limit=10):
    """Scans the designated Drive folder and populates the studio_vault table."""
    creds = get_google_creds()
    service = build('drive', 'v3', credentials=creds)
    
    print(f"Scanning Drive Folder ID: {VAULT_FOLDER_ID}...")
    items = find_all_images_in_folder(service, VAULT_FOLDER_ID)
    
    if not items:
        print("No image items found in the Vault folder.")
        return

    items = sorted(items, key=lambda x: x.get('createdTime', ''), reverse=True)
    items = items[:limit]

    for item in items:
        existing = supabase.table("studio_vault").select("id").eq("media_id", item['id']).execute()
        if existing.data:
            print(f"Skipping {item['name']} (Already in vault)")
            continue

        print(f"Analyzing {item['name']}...")
        
        base64_img = get_image_base64(service, item['id'])
        if not base64_img:
            continue
            
        analysis = analyze_image_with_ai(base64_img)
        
        if analysis and analysis.get('safe'):
            vault_entry = {
                "media_id": item['id'],
                "thumbnail_url": item.get('thumbnailLink', '').replace('=s220', '=s800'),
                "caption": analysis.get('caption', 'A moment in the studio.'),
                "aesthetic_score": analysis.get('score', 5),
                "status": "pending",
                "created_at": item.get('createdTime')
            }
            
            supabase.table("studio_vault").insert(vault_entry).execute()
            print(f"Added to Vault: {analysis.get('caption')}")
        else:
            print(f"Skipped {item['name']}: Image flagged as private or non-studio.")

if __name__ == "__main__":
    scan_drive_vault()
