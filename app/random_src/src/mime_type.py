import os
import requests
import mimetypes
import tempfile
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

# Simple Cache: Maps URL -> {"uri": file_uri, "name": file_name, "expiry": timestamp}
# In a real production app, store this in a database like Redis or SQLite
link_cache = {}

SUPPORTED_MIMES = [
    "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif", "image/gif",
    "video/mp4", "video/mpeg", "video/mov", "video/avi", "video/x-flv", "video/mpg", "video/webm", "video/wmv", "video/3gpp",
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/aac", "audio/adts", "audio/ogg", "audio/opus", "audio/flac",
    "application/pdf", "text/plain", "text/csv", "text/html", "text/markdown", "text/javascript", "text/x-python"
]

def get_mime_type(url):
    """Detects MIME type without hardcoding domains."""
    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        mime = resp.headers.get('Content-Type', '').split(';')[0].lower()
        if not mime or "octet-stream" in mime:
            guess, _ = mimetypes.guess_type(url)
            mime = guess if guess else "application/octet-stream"
        return mime
    except:
        return "application/octet-stream"

def agent_process_link(url, user_query="What is this?"):
    print(f"\n[Agent] Link Received: {url}")

    # 1. CHECK CACHE FIRST
    if url in link_cache:
        cached = link_cache[url]
        if time.time() < cached['expiry']:
            try:
                # Double check if Google still has it
                client.files.get(name=cached['name'])
                print("[Agent] Found in cache! Reusing existing file...")
                return call_gemini(cached['uri'], cached['mime'], user_query)
            except:
                print("[Agent] Cache expired on server side. Re-uploading...")
    mime_type = get_mime_type(url)
    if mime_type not in SUPPORTED_MIMES:
        print(f"❌ Unsupported format: {mime_type}")
        return

    # DOWNLOAD AND UPLOAD
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            r = requests.get(url, stream=True, timeout=15)
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024*1024):
                tmp.write(chunk)
            tmp_path = tmp.name

        print(f"[Agent] Uploading {mime_type}...")
        uploaded_file = client.files.upload(
            file=tmp_path, 
            config={'mime_type': mime_type}
        )

        # SAVE TO CACHE (Valid for 47 hours)
        link_cache[url] = {
            "uri": uploaded_file.uri,
            "name": uploaded_file.name,
            "mime": mime_type,
            "expiry": time.time() + (47 * 60 * 60)
        }

        # Cleanup local disk immediately
        os.remove(tmp_path)

        return call_gemini(uploaded_file.uri, mime_type, user_query)

    except Exception as e:
        print(f"❌ Error: {e}")

def call_gemini(file_uri, mime_type, query):
    """Makes the actual API call to the model."""
    print("[Agent] Analyzing...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_uri(file_uri=file_uri, mime_type=mime_type),
                types.Part.from_text(text=query)
            ]
        )
        print("\n--- AI Response ---")
        print(response.text)
        
        # NOTE: If you want to delete the file from Google right now:
        # file_name = file_uri.split('/')[-1]
        # client.files.delete(name=file_name)
        # print("[Agent] Cloud file deleted for privacy.")

    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    test_link = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNTBzcXRmNnNyMGpuNXFsenY5bjFtcGl2cDc3aWhwanFkZjFpczh3ayZlcD12MV9naWZzX3RyZW5kaW5nJmN0PWc/SEjPxNme8e6IWfaki9/giphy.gif"
    
    # First time: Downloads and Uploads
    agent_process_link(test_link)
    
    # Second time: Instant (Uses Cache)
    agent_process_link(test_link, "What does the text say?")
    # Test 2: A Public PDF Link
    # agent_process_link("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf")

    # Test 3: An Audio file
    # agent_process_link("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")