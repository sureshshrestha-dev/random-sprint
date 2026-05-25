import asyncio
import aiohttp

async def test_poison_queue():
    """Create a request that will permanently fail"""
    async with aiohttp.ClientSession() as session:
        # Send request with very high retries (still fails due to mock logic)
        async with session.post(
            "http://localhost:8000/generate",
            json={
                "user_id": "poison_test",
                "prompt": "This will fail permanently",
                "priority": "high",
                "max_retries": 1  # Will retry once, then poison
            }
        ) as resp:
            result = await resp.json()
            print(f"Initial response: {result}")
            request_id = result['request_id']
        
        # Wait for retries to exhaust
        print("Waiting for retries to exhaust...")
        await asyncio.sleep(30)
        
        # Check result
        async with session.get(f"http://localhost:8000/result/{request_id}") as resp:
            final = await resp.json()
            print(f"Final result: {final}")
        
        # Check poison queue
        async with session.get("http://localhost:8000/admin/dlq/poison") as resp:
            poison = await resp.json()
            print(f"Poison queue: {poison['poison_count']} items")

if __name__ == "__main__":
    asyncio.run(test_poison_queue())