import os
import json
import base64
from gcp_gemini_client import call_gemini

def run_tests():
    print("==========================================")
    print("      VERIFYING VERTEX AI (GEMINI)        ")
    print("==========================================")
    
    # Test 1: Simple Text Generation
    print("\n--- Test 1: Simple Text Generation ---")
    prompt_txt = "Say hello from Gemini on Google Cloud Vertex AI, and confirm that your engine is ready."
    print(f"Sending Prompt: {prompt_txt}")
    response = call_gemini(prompt_txt)
    print(f"Gemini Response: {response}")
    if response:
        print("Test 1 SUCCESS!")
    else:
        print("Test 1 FAILED!")
        return

    # Test 2: Multimodal Image Vision Analysis (JSON Output)
    print("\n--- Test 2: Multimodal Image Analysis (JSON) ---")
    test_img = "blue_logo.png"
    if not os.path.exists(test_img):
        test_img = "innov8_logo.png"
        
    if os.path.exists(test_img):
        print(f"Found test image: {test_img}. Encoding to base64...")
        with open(test_img, "rb") as f:
            img_bytes = f.read()
            
        system_prompt = "You are an AI assistant. Analyze the image and respond with a JSON object: {\"color\": \"string\", \"type_of_logo\": \"string\"}"
        prompt = "Analyze this image and describe its dominant color and logo style."
        
        print("Sending Vision Prompt to Gemini...")
        response_json = call_gemini(
            prompt=prompt,
            system_instruction=system_prompt,
            image_data=img_bytes,
            response_json=True
        )
        print(f"Gemini Response (JSON): {response_json}")
        if response_json:
            try:
                parsed = json.loads(response_json)
                print(f"Parsed Successfully: {parsed}")
                print("Test 2 SUCCESS!")
            except Exception as e:
                print(f"Failed to parse JSON output: {e}")
                print("Test 2 FAILED (JSON parse error)!")
        else:
            print("Test 2 FAILED!")
    else:
        print(f"Warning: No test image ({test_img}) found. Skipping Test 2.")

    print("\n==========================================")
    print("         VERIFICATION COMPLETE!           ")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
