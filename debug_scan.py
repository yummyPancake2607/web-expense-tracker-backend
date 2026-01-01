import os
import sys
import traceback
import base64

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

print(f"--- DEBUG SCRIPT v2 STARTED ---")
EXPECTED_PATH = os.path.join(current_dir, "service_account.json")
if os.path.exists(EXPECTED_PATH):
    print(f"[OK] service_account.json FOUND.")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = EXPECTED_PATH
else:
    print(f"[FAIL] service_account.json NOT FOUND.")
    sys.exit(1)

from google.cloud import vision

try:
    print("Attempting to instantiate Client...")
    client = vision.ImageAnnotatorClient()
    print("[OK] Client instantiated.")
    
    print("Attempting API Call (Text Detection)...")
    # Tiny 1x1 GIF as dummy content
    dummy_content = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    image = vision.Image(content=dummy_content)
    
    response = client.text_detection(image=image)
    print(f"[OK] API Call Success. Response received (Text annotations count: {len(response.text_annotations)})")
    
except Exception as e:
    print("[FAIL] API Call Failed.")
    traceback.print_exc()

print("--- DEBUG SCRIPT FINISHED ---")
