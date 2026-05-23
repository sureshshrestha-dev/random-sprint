from fastapi import Request
from fastapi.responses import JSONResponse
from database import get_redis
import os
import time
import psutil
import asyncio

# Configuration
CRITICAL_THRESHOLD = int(os.getenv("CRITICAL_LOAD_THRESHOLD", "80"))
WARNING_THRESHOLD = int(os.getenv("WARNING_LOAD_THRESHOLD", "60"))
CACHE_TTL = 2

# In-memory cache
_cached_load = {"value": 0, "last_updated": 0}

async def load_shedder_middleware(request: Request, call_next):
    global _cached_load
    
    now = time.time()
    if now - _cached_load["last_updated"] > CACHE_TTL:
        try:
            redis = await get_redis()
            val = await redis.get("system_load_stats")
            _cached_load["value"] = float(val) if val else 0
            _cached_load["last_updated"] = now
        except Exception as e:
            # If Redis fails, use last known value
            print(f"Failed to refresh load stats: {e}")
    
    system_load = _cached_load["value"] 
    if system_load > CRITICAL_THRESHOLD:
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            is_paid = await get_tenant_tier(tenant_id)
            if not is_paid:
                return JSONResponse(
                    status_code=503, 
                    content={"error": "System overloaded. Please try again later."}
                )
    response = await call_next(request)
    if system_load > WARNING_THRESHOLD:
        response.headers["X-System-Load"] = str(int(system_load))
    
    return response


async def start_load_monitoring(update_interval=5):
    """Start background task to monitor system load"""
    redis = await get_redis()
    
    while True:
        try:
            # Calculate system load
            if hasattr(psutil, 'getloadavg'):
                # Unix/Linux
                load_avg = psutil.getloadavg()[0]
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg / cpu_count) * 100
            else:
                # Windows
                load_percent = psutil.cpu_percent(interval=1)
            await redis.set("system_load_stats", round(load_percent, 2),ex=update_interval * 2)
            await redis.hset("system_metrics", mapping={
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "timestamp": asyncio.get_event_loop().time()
            })
            
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        await asyncio.sleep(update_interval)
