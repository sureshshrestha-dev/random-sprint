# test_client.py
import asyncio
import aiohttp
import json

async def test_gateway():
    """Test the AI Gateway"""
    
    async with aiohttp.ClientSession() as session:
        # Submit a request
        async with session.post(
            "http://localhost:8000/generate",
            json={
                "user_id": "test_user",
                "prompt": "What is the capital of France?",
                "priority": "normal",
                "max_retries": 3
            }
        ) as resp:
            result = await resp.json()
            request_id = result['request_id']
            print(f"Submitted: {result}")
        
        # Poll for result
        for _ in range(30):  # Poll for 30 seconds max
            await asyncio.sleep(1)
            async with session.get(f"http://localhost:8000/result/{request_id}") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"Result: {result}")
                    if result['status'] in ['completed', 'failed']:
                        break
                else:
                    print(f"Status: {resp.status}")
        
        # Check metrics
        async with session.get("http://localhost:8000/admin/metrics") as resp:
            metrics = await resp.json()
            print(f"Metrics: {json.dumps(metrics, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_gateway())