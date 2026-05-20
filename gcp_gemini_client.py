import os
import json
import base64
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = 'token_drive.json'
CLIENT_SECRET_FILE = 'client_secret.json'

def get_access_token():
    """Loads and automatically refreshes Google OAuth credentials from token_drive.json."""
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as f:
                    f.write(creds.to_json())
        return creds.token
    except Exception as e:
        print(f"[GEMINI CLIENT] Error loading/refreshing credentials: {e}")
        return None

def call_gemini(
    prompt, 
    system_instruction=None, 
    image_data=None, 
    audio_data=None, 
    image_mime="image/jpeg", 
    audio_mime="audio/mp3", 
    response_json=False, 
    model="gemini-2.5-flash"
):
    """
    Calls the Google Cloud Vertex AI Gemini API using standard REST requests.
    Supports text, images (base64 or bytes), audio (base64 or bytes), system prompts, and structured JSON formats.
    """
    token = get_access_token()
    if not token:
        print("[GEMINI CLIENT ERROR] No active token. Please run 'python setup_gcp_credentials.py' first.")
        return None
    
    # Read project_id from client_secret.json with fallback
    project_id = "studio-pulse-vault"
    if os.path.exists(CLIENT_SECRET_FILE):
        try:
            with open(CLIENT_SECRET_FILE, 'r') as f:
                cs = json.load(f)
                project_id = cs.get("installed", {}).get("project_id", project_id)
        except Exception as e:
            print(f"[GEMINI CLIENT] Warning: Could not parse client_secret.json: {e}")
            
    # Construct Vertex AI Regional API Endpoint
    url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}/locations/us-central1/publishers/google/models/{model}:generateContent"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    parts = []
    
    # 1. Base64 Image if provided
    if image_data:
        # Strip any standard base64 data-URL prefixes
        if isinstance(image_data, str) and "," in image_data:
            image_data = image_data.split(",", 1)[1]
        
        # Convert bytes to string if needed
        b64_str = image_data if isinstance(image_data, str) else base64.b64encode(image_data).decode('utf-8')
        parts.append({
            "inlineData": {
                "mimeType": image_mime,
                "data": b64_str
            }
        })
        
    # 2. Base64 Audio if provided
    if audio_data:
        # Convert bytes to string if needed
        b64_str = audio_data if isinstance(audio_data, str) else base64.b64encode(audio_data).decode('utf-8')
        parts.append({
            "inlineData": {
                "mimeType": audio_mime,
                "data": b64_str
            }
        })
        
    # 3. Text Prompt
    parts.append({
        "text": prompt
    })
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ]
    }
    
    # 4. System Instruction Setup
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [
                {
                    "text": system_instruction
                }
            ]
        }
        
    # 5. Generation Config Setup (e.g. structured JSON formatting)
    generation_config = {}
    if response_json:
        generation_config["responseMimeType"] = "application/json"
        
    if generation_config:
        payload["generationConfig"] = generation_config
        
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code == 200:
            resp_data = response.json()
            try:
                text_content = resp_data['candidates'][0]['content']['parts'][0]['text']
                return text_content
            except (KeyError, IndexError) as err:
                print(f"[GEMINI CLIENT ERROR] Failed to parse API response structure: {err}. Response text: {response.text}")
                return None
        else:
            print(f"[GEMINI CLIENT ERROR] Vertex AI HTTP {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[GEMINI CLIENT ERROR] Request failed: {e}")
        return None
