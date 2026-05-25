import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import asyncio

from datetime import datetime
load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

SYSTEM_INSTRUCTIONS = os.getenv("SYSTEM_INSTRUCTIONS", "")


async def setup_and_use_cache():
    model = "gemini-2.5-flash"
    cache = client.caches.create(
        model=model,
        config=types.CreateCachedContentConfig(
            display_name="Ambition Guru Books Assistant",
            system_instruction=SYSTEM_INSTRUCTIONS,
            ttl="3600s",
        )
    )
    
    print(f"Cache created: {cache.name}")
    print(f"Cache tokens: {cache.usage_metadata.total_token_count}")
    
    user_requests = [
        "Hiun Ko Geet ko price kati ho?",
        "pp",
        "delivery time kati lagcha?"
    ]
    
    for i, request in enumerate(user_requests, 1):
        response = client.models.generate_content(
            model=model,
            contents=request,
            config=types.GenerateContentConfig(
                cached_content=cache.name
            )
        )
        
        print(f"\n--- Request {i} ---")
        print(f"User: {request}")
        print(f"Response: {response.text}")
        
        # FIXED: Access cached tokens correctly
        usage = response.usage_metadata
        print(f"Total prompt tokens: {usage.prompt_token_count}")
        
        if usage.cache_tokens_details:
            cached_tokens = usage.cache_tokens_details[0].token_count
            print(f"Cached tokens: {cached_tokens}")
            cache_hit_rate = (cached_tokens / usage.prompt_token_count) * 100
            print(f"Cache hit rate: {cache_hit_rate:.1f}%")
        else:
            print("No cached tokens used")
        
        print(f"Response tokens: {usage.candidates_token_count}")
        print(f"Total tokens: {usage.total_token_count}")
    
    # STEP 3: Optional - Clean up
    # client.caches.delete(name=cache.name)
    # print("\nCache deleted")

async def list_and_manage_caches():
    """List all existing caches and their status"""
    print("\n=== Managing Caches ===")
    caches = list(client.caches.list())
    
    if not caches:
        print("No caches found")
        return
    
    for cache in caches:
        print(f"\nCache: {cache.name}")
        print(f"  Display: {cache.display_name}")
        print(f"  Model: {cache.model}")
        print(f"  Created: {cache.create_time}")
        print(f"  Expires: {cache.expire_time}")
        print(f"  Tokens: {cache.usage_metadata.total_token_count}")
    
        if cache.expire_time:
            # Cache has expiration time
            print(f"  Status: Active until {cache.expire_time}")
        else:
            print(f"  Status: Active (no expiration)")

async def extend_cache_lifetime(cache_name):
    """Extend existing cache lifetime"""
    client.caches.update(
        name=cache_name,
        config=types.UpdateCachedContentConfig(
            ttl="24h" 
        )
    )
    print(f"Cache {cache_name} extended to 24 hours")s
asyncio.run(setup_and_use_cache())
