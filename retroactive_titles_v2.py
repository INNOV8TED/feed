import os
import random
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(URL, KEY)

LABEL_POOL = {
    "edit":     ["Cutting the Master", "Timeline Sculpting", "Visual Storytelling", "Assembly Phase", "Edit Lock In Progress", "Color Correction", "Master Render Phase"],
    "motion":   ["Visual Synthesis", "Dynamic Simulation", "After Effects Magic", "Kinetic Design", "FX Pass", "Animating Reality"],
    "graphic":  ["Visual Prototyping", "Digital Alchemy", "Aesthetic Refinement", "Composition Phase", "Pixel Perfecting", "Texture Mapping", "Branding Forge"],
    "audio":    ["Sonic Engineering", "Melodic Synthesis", "Frequency Sculpting", "Mixing Session", "Atmospheric Layering", "Rhythm Engine Active"]
}

MAPPING = {
    "Deep in the Edit": "edit",
    "Exporting Final Render": "edit",
    "Color Grading HERO shot": "edit",
    "Motion Graphics & FX": "motion",
    "Graphic Design": "graphic",
    "Audio Mastering": "audio"
}

def main():
    print(">>> Fetching all pulses...")
    res = supabase.table("studio_heartbeat").select("*").execute()
    pulses = res.data
    
    print(f">>> Processing {len(pulses)} pulses...")
    
    updates = []
    for p in pulses:
        label = p.get("action_label")
        if label in MAPPING:
            category = MAPPING[label]
            new_label = random.choice(LABEL_POOL[category])
            updates.append({"id": p["id"], "action_label": new_label})
    
    print(f">>> Found {len(updates)} pulses to update. Executing...")
    
    success_count = 0
    for up in updates:
        try:
            supabase.table("studio_heartbeat").update({"action_label": up["action_label"]}).eq("id", up["id"]).execute()
            success_count += 1
            if success_count % 20 == 0:
                print(f"--- Updated {success_count} pulses...")
        except Exception as e:
            print(f"--- [ERROR] ID {up['id']}: {e}")
            
    print(f">>> Finished! Successfully updated {success_count} pulses.")

if __name__ == "__main__":
    main()
