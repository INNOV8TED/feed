import os

file_path = r"C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\activity_feed\heartbeat.py"
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Identify the range to delete
start_line = 0
end_line = 0
for i, line in enumerate(lines):
    if "PRODUCTION-ONLY FILTER (Video/Audio)" in line and i > 1000:
        start_line = i
    if "broadcast_to_buffer(msg_story" in line and i > 1400:
        end_line = i + 1

if start_line > 0 and end_line > start_line:
    print(f"Deleting lines {start_line+1} to {end_line+1}")
    new_lines = lines[:start_line] + lines[end_line+1:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Success")
else:
    print(f"Failed to find markers. Start: {start_line}, End: {end_line}")
