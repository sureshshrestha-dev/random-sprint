# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from ai_gateway.models import GenerateRequest, GenerateResponse, ResultResponse, CircuitStateResponse
from ai_gateway.gemini_client import ReliableGeminiClient
from core.database import redis_manager
from ai_gateway.config import config
from ai_gateway.dlq_worker import DLQRecoveryWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
gemini_client = None
redis_conn = None
dlq_worker_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global gemini_client, redis_conn, dlq_worker_task
    
    # Startup
    logger.info("Starting AI Gateway...")
    
    # Connect to Redis
    redis_conn = await redis_manager.connect(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )
    
    # Initialize Gemini client
    gemini_client = ReliableGeminiClient(redis_conn)
    
    # Start DLQ recovery worker in background
    worker = DLQRecoveryWorker(gemini_client, redis_conn)
    dlq_worker_task = asyncio.create_task(worker.run())
    
    logger.info("AI Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Gateway...")
    if dlq_worker_task:
        dlq_worker_task.cancel()
    await redis_manager.close()
    logger.info("Shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="AI Gateway",
    description="Production AI Gateway with Rate Limiting, Circuit Breaker, and DLQ",
    version="1.0.0",
    lifespan=lifespan
)

# Load shedding middleware (inbound rate limiting)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time

class LoadShedderMiddleware(BaseHTTPMiddleware):
    """Protect our servers from being overwhelmed"""
    
    def __init__(self, app, max_requests_per_second: int = 100):
        super().__init__(app)
        self.max_requests_per_second = max_requests_per_second
        self.requests_in_current_second = 0
        self.current_second = int(time.time())
    
    async def dispatch(self, request, call_next):
        now = int(time.time())
        
        # Reset counter if new second
        if now != self.current_second:
            self.current_second = now
            self.requests_in_current_second = 0
        
        # Check if overloaded
        if self.requests_in_current_second >= self.max_requests_per_second:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "Server overloaded - please retry with backoff"}
            )
        
        self.requests_in_current_second += 1
        return await call_next(request)

# Add middlewares
app.add_middleware(LoadShedderMiddleware, max_requests_per_second=config.MAX_CONCURRENT_REQUESTS)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Configure as needed

# API Endpoints
@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Submit a generation request.
    Returns immediately - poll /result/{request_id} for actual result.
    """
    result = await gemini_client.generate_with_dlq(request)
    return GenerateResponse(**result)

@app.get("/result/{request_id}", response_model=ResultResponse)
async def get_result(request_id: str):
    """Poll for completed request results"""
    # Check if result exists
    result_data = await redis_conn.get(f"result:{request_id}")
    
    if result_data:
        # result_data is already a dict (deserialized by RedisClient.get)
        return ResultResponse(
            status="completed" if "result" in result_data else "failed",
            request_id=request_id,
            result=result_data.get("result"),
            completed_at=result_data.get("completed_at")
        )
    
    # Check if still in DLQ (pending)
    for queue in ["gemini:dlq:high", "gemini:dlq:normal"]:
        jobs = await redis_conn.lrange(queue, 0, -1)
        for job_json in jobs:
            import json
            job = json.loads(job_json)
            if job['request_id'] == request_id:
                return ResultResponse(
                    status="pending",
                    request_id=request_id,
                    result=None
                )
    
    # Check delayed queue
    delayed_jobs = await redis_conn.zrange("gemini:dlq:delayed", 0, -1)
    for job_json in delayed_jobs:
        import json
        job = json.loads(job_json)
        if job['request_id'] == request_id:
            return ResultResponse(
                status="pending",
                request_id=request_id,
                result=None
            )
    
    raise HTTPException(status_code=404, detail="Request not found or expired")

@app.get("/admin/metrics")
async def get_metrics():
    """Get system metrics (admin only - add auth in production)"""
    metrics = await gemini_client.get_metrics()
    return metrics

@app.get("/admin/circuit-breaker", response_model=CircuitStateResponse)
async def get_circuit_state():
    """Get current circuit breaker state"""
    state = await gemini_client.circuit_breaker.get_state()
    return CircuitStateResponse(**state)

@app.post("/admin/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Manually reset circuit breaker (admin only)"""
    await gemini_client.circuit_breaker._record_success()  # Force close
    return {"status": "circuit breaker reset"}

@app.get("/admin/dlq/poison")
async def get_poison_queue(limit: int = 100):
    """View poison queue for manual inspection"""
    items = await redis_conn.lrange("gemini:poison", 0, limit - 1)
    import json
    return {"poison_count": len(items), "items": [json.loads(item) for item in items]}

@app.delete("/admin/dlq/poison")
async def clear_poison_queue():
    """Clear poison queue (after manual resolution)"""
    await redis_conn.delete("gemini:poison")
    return {"status": "poison queue cleared"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "redis": await redis_conn.ping(),
        "circuit_state": (await gemini_client.circuit_breaker.get_state())["state"]
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "AI Gateway",
        "version": "1.0.0",
        "endpoints": {
            "POST /generate": "Submit generation request",
            "GET /result/{request_id}": "Poll for result",
            "GET /admin/metrics": "System metrics",
            "GET /health": "Health check"
        }
    }


    # uvicorn ai_gateway.main:app --host 127.0.0.1 --port 8000

    # # Watch metrics in real-time
# watch -n 2 'curl -s http://localhost:8000/admin/metrics | python3 -m json.tool'

# Check DLQ sizes
curl -s http://localhost:8000/admin/metrics | jq '.dlq_lengths'

# Reset circuit breaker manually (if needed)
# curl -X POST http://localhost:8000/admin/circuit-breaker/reset

# View poison queue for debugging
# curl -s http://localhost:8000/admin/dlq/poison | jq '.'

# Clear poison queue (after fixing the issue)
# curl -X DELETE http://localhost:8000/admin/dlq/poison