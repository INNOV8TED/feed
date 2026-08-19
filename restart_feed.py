import os
import sys
import time
import subprocess
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

def log(msg):
    print(f"[RESTART] {msg}")

def kill_existing_heartbeat():
    log("Checking for running heartbeat instances...")
    try:
        import psutil
        current_pid = os.getpid()
        killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python.exe' and proc.info['pid'] != current_pid:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'heartbeat.py' in cmdline:
                        log(f"Terminating old heartbeat process (PID {proc.info['pid']})...")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except Exception:
                            proc.kill()
                        killed += 1
            except Exception:
                pass
        if killed == 0:
            log("No running heartbeat daemon found.")
        else:
            log(f"Successfully stopped {killed} old heartbeat process(es).")
    except ImportError:
        subprocess.run('taskkill /F /FI "WINDOWTITLE eq *heartbeat*" /T', shell=True, capture_output=True)

    lock_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heartbeat.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            log("Cleaned up stale heartbeat.lock.")
        except Exception:
            pass

def verify_credentials():
    log("Verifying Supabase credentials...")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        log("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env!")
        return False

    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/studio_heartbeat?select=id&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"}
        )
        resp = urllib.request.urlopen(req, timeout=8)
        if resp.status == 200:
            log("Supabase database connection: OK (authenticated)")
            return True
    except Exception as e:
        log(f"WARNING: Supabase connection test failed: {e}")
        return False

def check_live_feed():
    log("Checking live feed status at https://feed.in-no-v8.com/...")
    try:
        req = urllib.request.Request("https://feed.in-no-v8.com/", headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=8)
        if resp.status == 200:
            log("Live feed endpoint: OK (200)")
            return True
    except Exception as e:
        log(f"WARNING: Live feed check returned: {e}")
        return False

def start_heartbeat():
    log("Starting Studio Pulse heartbeat daemon...")
    vbs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silent_heartbeat.vbs")
    if os.path.exists(vbs_path):
        subprocess.run(f'cscript //nologo "{vbs_path}"', shell=True)
    else:
        subprocess.Popen([sys.executable, "heartbeat.py"], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

    time.sleep(2)
    log("Heartbeat daemon launched in background.")
    log("Studio Pulse is actively monitoring your workstation.")

def main():
    print("=" * 60)
    print("      STUDIO PULSE FEED // RESTORE & RESTART UTILITY")
    print("=" * 60)
    kill_existing_heartbeat()
    verify_credentials()
    check_live_feed()
    start_heartbeat()
    print("=" * 60)
    print("  SUCCESS: Studio Pulse has been refreshed and is monitoring.")
    print("  Feed is live at: https://feed.in-no-v8.com/")
    print("=" * 60)

if __name__ == "__main__":
    main()
