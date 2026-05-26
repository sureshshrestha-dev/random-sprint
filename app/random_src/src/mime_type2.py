import os
import json
import requests
import mimetypes
import tempfile
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

# --- PERSISTENT CACHE LOGIC ---
CACHE_FILE = "link_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

# Global Cache Object
link_cache = load_cache()

def get_or_upload_link(url):
    """Checks cache for a URI; if not found, downloads and uploads to Gemini."""
    global link_cache
    
    # 1. Check disk-based cache
    if url in link_cache:
        cached = link_cache[url]
        if time.time() < cached['expiry']:
            try:
                # Verify file still exists on Google's end
                client.files.get(name=cached['name'])
                print(f"[Agent] Reusing cached file for: {url[:30]}...")
                return cached
            except:
                print("[Agent] Cloud file expired. Re-uploading...")

    # 2. Upload if not in cache
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                tmp.write(chunk)
            tmp_path = tmp.name

        mime_type, _ = mimetypes.guess_type(url)
        # Handle Giphy/Sticker edge case
        if not mime_type or "gif" in url: mime_type = "image/gif"

        print(f"[Agent] Uploading new link: {url[:30]}...")
        uploaded_file = client.files.upload(file=tmp_path, config={'mime_type': mime_type})
        os.remove(tmp_path)

        # Update and save cache
        cache_entry = {
            "uri": uploaded_file.uri,
            "name": uploaded_file.name,
            "mime": mime_type,
            "expiry": time.time() + (47 * 60 * 60)
        }
        link_cache[url] = cache_entry
        save_cache(link_cache)
        return cache_entry

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def compare_links(url1, url2, query="Compare these two images."):
    """Takes two links and sends BOTH URIs to Gemini in one request."""
    
    file1 = get_or_upload_link(url1)
    file2 = get_or_upload_link(url2)

    if not file1 or not file2:
        print("Could not process one of the links.")
        return

    print("[Agent] Comparing files...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_uri(file_uri=file1['uri'], mime_type=file1['mime']),
            types.Part.from_uri(file_uri=file2['uri'], mime_type=file2['mime']),
            types.Part.from_text(text=query)
        ]
    )
    
    print("\n--- AI Comparison Response ---")
    print(response.text)

if __name__ == "__main__":
    link_a = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNTBzcXRmNnNyMGpuNXFsenY5bjFtcGl2cDc3aWhwanFkZjFpczh3ayZlcD12MV9naWZzX3RyZW5kaW5nJmN0PWc/SEjPxNme8e6IWfaki9/giphy.gif"
    link_b = "https://media.giphy.com/media/3o7TKMGpxvF1V6tS8M/giphy.gif" # A different GIF

    compare_links(link_a, link_b, "Describe the difference in mood between these two GIFs.")