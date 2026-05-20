import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token_drive.json'
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/cloud-platform'
]

def setup_gcp_creds():
    print("====================================================")
    print("      GOOGLE CLOUD + DRIVE OAUTH AUTHENTICATION     ")
    print("====================================================")
    print("This script will re-authenticate you to include both:")
    print("1. Google Drive (required to read/write files)")
    print("2. Google Cloud Platform (required to use Vertex AI Gemini under your credits)")
    print("\nStarting local authentication server...")
    
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"ERROR: {CLIENT_SECRET_FILE} not found. Cannot proceed.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    # Open local server for OAuth handshake
    creds = flow.run_local_server(port=0)
    
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print("\n====================================================")
    print(f"SUCCESS: Authentication complete! Saved to {TOKEN_FILE}")
    print("Both Google Drive and Vertex AI are ready to use.")
    print("====================================================")

if __name__ == "__main__":
    setup_gcp_creds()
