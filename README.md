# IN-NO-V8 Live News Engine (v1.0)

A professional, automated studio activity feed and social media broadcasting system. This engine monitors the local INNOV8 workspace in Chiang Mai and synchronizes activity in real-time with a live-blogging dashboard and social media.

## 🚀 Features

- **Intelligent Heartbeat**: Recursively monitors `ACTIVE_WORK` for production file changes (Premiere, After Effects, Photoshop, FL Studio).
- **Direct Buffer Integration**: Automated social media broadcasting via Buffer GraphQL API. Triggered specifically by folders named `PUBLISH`.
- **Dynamic Theming**: The live dashboard automatically switches visual themes based on the active project (e.g., Gold/Organic for *Lanna Whispers*, Cyan/Digital for *A-CAM*).
- **Self-Healing Architecture**: Automatic reconnection logic for resilience against network drops and system hibernation.
- **Security Hardened**: Full environment variable support (`.env`) to keep API keys private.

## 🛠️ Technical Stack

- **Backend**: Python 3.x, `watchdog`, `supabase-py`, `requests`, `python-dotenv`.
- **Frontend**: HTML5, Vanilla CSS (Dynamic Variables), Supabase Realtime JS.
- **Automation**: Windows Task Scheduler + Silent VBS Launcher.

## 📂 Project Structure

- `heartbeat.py`: The core monitoring and broadcasting engine.
- `index.html`: The real-time "Pulse Stream" dashboard.
- `.env`: (Local Only) Storage for Supabase and Buffer credentials.
- `lanna_sprite.png` / `acam_sprite.png`: Project-specific visual assets.

## ⚙️ Setup

1. **Environment**: Install dependencies via `pip install watchdog supabase python-dotenv requests`.
2. **Configuration**: Create a `.env` file with your `SUPABASE_URL`, `SUPABASE_KEY`, `BUFFER_ACCESS_TOKEN`, and `BUFFER_PROFILE_ID`.
3. **Database**: Ensure the `studio_heartbeat` table in Supabase has the `is_milestone` (boolean) and `project_name` (text) columns.
4. **Launch**: Run `heartbeat.py` or use the included `.vbs` launcher for silent background operation.

---
*Created by IN-NO-V8 Studios | Chiang Mai*
