import subprocess
import json
import os

def get_dims(path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(res.stdout)
    return data['streams'][0]['width'], data['streams'][0]['height']

dir_path = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\SOCIAL\LANNA"
for f in os.listdir(dir_path):
    if f.lower().endswith(('.mp4', '.mov')):
        w, h = get_dims(os.path.join(dir_path, f))
        print(f"{f}: {w}x{h}")
