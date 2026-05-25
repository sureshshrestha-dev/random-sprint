import os
from google import genai
from dotenv import load_dotenv
import asyncio
from openai import AsyncOpenAI
load_dotenv()

SYSTEM_INSTRUCTIONS = os.getenv("SYSTEM_INSTRUCTIONS", "")

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def test_with_openai():
    response1 = await client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": "Hiun Ko Geet ko price kati ho?"}
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"Response 1: {response1.choices[0].message.content}")
    print(f"Prompt tokens: {response1.usage.prompt_tokens}")
    print(f"Cached tokens: {response1.usage.prompt_tokens_details.cached_tokens}")
    cached_pct = (response1.usage.prompt_tokens_details.cached_tokens / response1.usage.prompt_tokens) * 100
    print(f"Cache hit rate: {cached_pct:.1f}%")
    
    # Second request (should hit cache!)
    response2 = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTIONS},
            {"role": "user", "content": "pp"}  
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    print(f"\nResponse 2: {response2.choices[0].message.content}")
    print(f"Prompt tokens: {response2.usage.prompt_tokens}")
    print(f"Cached tokens: {response2.usage.prompt_tokens_details.cached_tokens}")
    cached_pct2 = (response2.usage.prompt_tokens_details.cached_tokens / response2.usage.prompt_tokens) * 100
    print(f"Cache hit rate: {cached_pct2:.1f}%")

asyncio.run(test_with_openai())