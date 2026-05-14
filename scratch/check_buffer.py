import os
import requests
import json

BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")

def list_profiles():
    url = "https://api.bufferapp.com/1/profiles.json"
    headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            profiles = response.json()
            for p in profiles:
                print(f"ID: {p['id']} | Service: {p['service']} | Formatted Name: {p['formatted_username']}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_profiles()
