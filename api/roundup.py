from http.server import BaseHTTPRequestHandler
import os
import requests
import json
from datetime import datetime, timedelta
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. Configuration
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        BUFFER_TOKEN = os.environ.get("BUFFER_ACCESS_TOKEN")
        BUFFER_PROFILE_ID = os.environ.get("BUFFER_PROFILE_ID")

        if not all([SUPABASE_URL, SUPABASE_KEY, BUFFER_TOKEN, BUFFER_PROFILE_ID]):
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Missing environment variables.")
            return

        # 2. Fetch Activity (Last 12 Hours)
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        time_limit = (datetime.utcnow() - timedelta(hours=12)).isoformat()
        
        try:
            response = supabase.table("studio_heartbeat") \
                .select("*") \
                .gte("created_at", time_limit) \
                .execute()
            pings = response.data
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Supabase Error: {e}".encode())
            return

        # 3. Summarize Activity
        if not pings:
            summary = "A quiet day of deep-focus and planning at INNOV8 Studios."
        else:
            projects = {}
            milestones = 0
            for p in pings:
                name = p.get('project_name', 'General Lab')
                projects[name] = projects.get(name, 0) + 1
                if p.get('is_milestone'):
                    milestones += 1
            
            summary_parts = [f"{count} updates in #{proj}" for proj, count in projects.items()]
            summary = f"A massive day in the lab with {len(projects)} active projects. "
            summary += ", ".join(summary_parts) + ". "
            if milestones > 0:
                summary += f"Hit {milestones} major milestones along the way."
            summary += "\n\nCheck the live pulse at feed.in-no-v8.com."

        # 4. Broadcast to Buffer
        url = "https://api.buffer.com"
        query = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id } }
            ... on MutationError { message }
          }
        }
        """
        variables = {
            "input": {
                "text": summary,
                "channelId": BUFFER_PROFILE_ID,
                "schedulingType": "automatic",
                "mode": "addToQueue",
                "assets": { "images": [{"url": "https://feed.in-no-v8.com/stephen_focus_vertical.png"}] },
                "metadata": { "instagram": { "type": "story", "shouldShareToFeed": False } }
            }
        }
        
        headers = {"Authorization": f"Bearer {BUFFER_TOKEN}"}
        r = requests.post(url, json={"query": query, "variables": variables}, headers=headers)

        # 5. Response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"success": True, "narrative": summary, "buffer_status": r.status_code}).encode())
        return
