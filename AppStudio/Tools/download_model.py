"""Download Vosk speech recognition model for Quarky_Ai voice mode."""
import urllib.request
import zipfile
import os

URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
ZIP_PATH = "models/vosk-model-small-en-us-0.15.zip"
EXTRACT_DIR = "models/"

os.makedirs(EXTRACT_DIR, exist_ok=True)

print("Downloading Vosk model (~40MB)...")
urllib.request.urlretrieve(URL, ZIP_PATH)
print("Download complete. Extracting...")

with zipfile.ZipFile(ZIP_PATH) as zf:
    zf.extractall(EXTRACT_DIR)

os.remove(ZIP_PATH)
print(f"Done! Model extracted to {EXTRACT_DIR}vosk-model-small-en-us-0.15/")
