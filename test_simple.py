import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/generate",
            json={
                "user_id": "test",
                "prompt": "Hello"
            }
        ) as resp:
            text = await resp.text()
            print(f"Status: {resp.status}")
            print(f"Content-Type: {resp.headers.get('Content-Type')}")
            print(f"Response: {text}")

asyncio.run(test())
