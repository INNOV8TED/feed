import json
import os
import requests
import base64
from gcp_gemini_client import call_gemini

def process_inventory(limit=10):
    with open('vault_inventory.json', 'r') as f:
        data = json.load(f)
        
    processed = 0
    for item in data:
        if processed >= limit:
            break
            
        # Skip items we've already tagged or that don't have images
        if 'vision_tags' in item:
            continue
        if not item.get('image_path') or not item.get('zip_id'):
            continue
            
        print(f"Processing: {item['image_path']}")
        
        # We can fetch the image directly from our new vault_server backend!
        img_url = f"http://127.0.0.1:8000/image?path={item['image_path']}&zip_id={item['zip_id']}&zip_size={item['zip_size']}"
        try:
            r = requests.get(img_url)
            if r.status_code == 200:
                base64_img = base64.b64encode(r.content).decode('utf-8')
                
                system_instruction = "You are a visual archivist curating a public, location-based interactive map. If the image is a portrait, selfie, or heavily person-centric (personal/family photos), respond ONLY with the exact array [\"PERSONAL_REJECT\"]. Otherwise, if it is a nice location-based image (landmarks, street photography, architecture, landscape), respond ONLY with a JSON array of 3-5 short, descriptive category tags (e.g. [\"Urban\", \"Architecture\", \"Night\", \"Neon\"]). Do not include markdown backticks or any other text."
                prompt = "Analyze this image and return the JSON array of tags."
                
                print(" -> Requesting tags from Gemini...")
                content = call_gemini(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    image_data=base64_img,
                    response_json=True
                )
                
                if content:
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content.replace('```json', '').replace('```', '')
                    
                    try:
                        tags = json.loads(content)
                        item['vision_tags'] = tags
                        print(f" -> AI Tags generated: {tags}")
                        processed += 1
                    except json.JSONDecodeError:
                        print(f" -> Failed to parse AI output: {content}")
                else:
                    print(" -> Gemini API Error")
            else:
                print(f" -> Failed to fetch from vault_server: {r.status_code}")
                
        except Exception as e:
            print(f"Failed to process {item['image_path']}: {e}")
            
    # Save incrementally
    if processed > 0:
        with open('vault_inventory.json', 'w') as f:
            json.dump(data, f)
        print(f"\nSuccessfully tagged {processed} images. Run again to process more.")
    else:
        print("\nNo new images were processed.")

if __name__ == "__main__":
    # We set a limit of 10 for the initial batch to conserve credits.
    # The user can increase this when they are ready to run the full archive.
    process_inventory(limit=10)
