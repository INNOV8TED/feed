import os
import requests
import json
from datetime import datetime, timedelta
from supabase import create_client
from dotenv import load_dotenv

# Load configuration
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")

def get_daily_activity():
    """Fetch the last 12 hours of activity from Supabase."""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Calculate time 12 hours ago
    time_limit = (datetime.utcnow() - timedelta(hours=12)).isoformat()
    
    try:
        response = supabase.table("studio_heartbeat") \
            .select("*") \
            .gte("created_at", time_limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching logs: {e}")
        return []

def summarize_activity(pings):
    """Analyze the pings and format them for an AI summary."""
    if not pings:
        return "A quiet day of planning and deep-work in the lab."
    
    projects = {}
    milestones = 0
    
    for p in pings:
        name = p.get('project_name', 'General Lab')
        projects[name] = projects.get(name, 0) + 1
        if p.get('is_milestone'):
            milestones += 1
            
    # Narrative Builder (Template)
    summary_parts = []
    for proj, count in projects.items():
        summary_parts.append(f"{count} updates in #{proj}")
        
    narrative = f"A massive day in the lab with {len(projects)} active projects. "
    narrative += ", ".join(summary_parts) + ". "
    if milestones > 0:
        narrative += f"Hit {milestones} major milestones along the way. "
    
    narrative += "\n\nCheck the live pulse at feed.in-no-v8.com."
    return narrative

def broadcast_to_buffer(text, image_url):
    """Post the summary to Buffer."""
    url = "https://api.buffer.com"
    
    query = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    
    variables = {
        "input": {
            "text": text,
            "channelId": BUFFER_PROFILE_ID,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": {
                "images": [{"url": image_url}]
            },
            "metadata": {
                "instagram": {
                    "type": "post",
                    "shouldShareToFeed": True
                }
            }
        }
    }
    
    headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
    try:
        r = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        print(f"Roundup Sent! Buffer response: {r.status_code}")
    except Exception as e:
        print(f"Broadcast error: {e}")

if __name__ == "__main__":
    print("Gathering today's studio narrative...")
    activities = get_daily_activity()
    story = summarize_activity(activities)
    
    # Select Hero Image (For now, use your favorite Stephen sprite)
    hero_image = "https://feed.in-no-v8.com/stephen_focus.png"
    
    print(f"Generated Narrative:\n{story}")
    
    # Broadcast
    broadcast_to_buffer(story, hero_image)
