import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import sys

class SimpleHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        print(f"EVENT: {event}", flush=True)

if __name__ == "__main__":
    path = "C:\\Users\\Stephen Portman\\Desktop\\ACTIVE_WORK"
    print(f"Watching {path}...", flush=True)
    event_handler = SimpleHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
