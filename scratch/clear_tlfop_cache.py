
import json
import os

CACHE_FILE = "studio_cache.json"

def clear_cache_for_tlfop():
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found.")
        return

    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)

    # Cache structure has "size_cache" and "fingerprints"
    size_cache = cache.get("size_cache", {})
    fingerprints = cache.get("fingerprints", {})

    print(f"Original size_cache: {len(size_cache)}")
    
    new_size_cache = {k: v for k, v in size_cache.items() if "TLFOP" not in k}
    new_fingerprints = {k: v for k, v in fingerprints.items() if "TLFOP" not in k} # Note: fingerprints keys are hashes, so we might not be able to filter by path easily
    
    # Actually fingerprints keys are the path! 
    # Wait, let's check a few keys
    for k in list(size_cache.keys())[:5]:
        print(f"Sample key: {k}")

    cache["size_cache"] = new_size_cache
    # fingerprints keys might not have TLFOP in them if they are just hashes, 
    # but in heartbeat.py: fingerprint = f"{stat.st_size}_{stat.st_mtime}" 
    # Wait! The KEY is the fingerprint, not the path.
    # fingerprint_cache[fingerprint] = time.time()
    # So we can't easily clear fingerprints by path. 
    # But size_cache uses path as key.
    
    print(f"New size_cache: {len(new_size_cache)}")
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)
    
    print("◈ [SUCCESS] TLFOP cleared from cache. Restart heartbeat to re-index.")

if __name__ == "__main__":
    clear_cache_for_tlfop()
