from fastapi import FastAPI
from app.load_shedding.middleware import load_shedder_middleware, update_system_load_metrics
import asyncio
from database import get_redis
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    monitoring_task = asyncio.create_task(start_load_monitoring())
    yield
    # Shutdown
    monitoring_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Hello World"}

