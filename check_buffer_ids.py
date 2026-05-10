import os
import requests
from dotenv import load_dotenv

def list_profiles():
    load_dotenv()
    token = os.environ.get("BUFFER_ACCESS_TOKEN")
    if not token:
        print("Error: No BUFFER_ACCESS_TOKEN found.")
        return

    url = "https://api.buffer.com"
    query = """
    query {
      account {
        profiles {
          id
          service
          service_username
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.post(url, json={"query": query}, headers=headers)
    if res.status_code == 200:
        data = res.json()
        if "errors" in data:
            print(f"GraphQL Error: {data['errors']}")
        else:
            profiles = data['data']['account']['profiles']
            print("\n◈ AVAILABLE BUFFER PROFILES ◈")
            for p in profiles:
                print(f"- {p['service']} ({p['service_username']}): ID = {p['id']}")
    else:
        print(f"Error: {res.status_code} - {res.text}")

if __name__ == "__main__":
    list_profiles()
