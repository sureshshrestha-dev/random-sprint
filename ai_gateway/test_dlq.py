# Create a test script: test_dlq.py
import asyncio
import aiohttp
import json

async def test_rate_limit():
    """Send 20 requests rapidly to trigger rate limiting"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(20):
            tasks.append(session.post(
                "http://localhost:8000/generate",
                json={
                    "user_id": f"test_user_{i}",
                    "prompt": f"Request number {i}",
                    "priority": "normal",
                    "max_retries": 3
                }
            ))
        
        responses = await asyncio.gather(*tasks)
        
        for resp in responses:
            result = await resp.json()
            print(f"Status: {result['status']}, Request ID: {result['request_id']}")
        
        # Check DLQ size
        async with session.get("http://localhost:8000/admin/metrics") as resp:
            metrics = await resp.json()
            print(f"\nDLQ Lengths: {metrics['dlq_lengths']}")
            print(f"Metrics: {metrics['metrics']}")

if __name__ == "__main__":
    asyncio.run(test_rate_limit())