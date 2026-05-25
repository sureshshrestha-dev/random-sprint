import asyncio
import aiohttp
import json

async def test_circuit_breaker():
    """Force multiple failures to trip the circuit breaker"""
    async with aiohttp.ClientSession() as session:
        # The mock has 10% failure rate, so send 50 requests
        for i in range(50):
            async with session.post(
                "http://localhost:8000/generate",
                json={
                    "user_id": "circuit_test",
                    "prompt": f"Test {i}",
                    "priority": "normal",
                    "max_retries": 1  # Low retries to fail faster
                }
            ) as resp:
                result = await resp.json()
                print(f"Request {i}: {result['status']}")
            
            # Check circuit state every 10 requests
            if i % 10 == 0:
                async with session.get("http://localhost:8000/admin/circuit-breaker") as resp:
                    state = await resp.json()
                    print(f"Circuit state: {state['state']}")
            
            await asyncio.sleep(0.1)  # Small delay

if __name__ == "__main__":
    asyncio.run(test_circuit_breaker())