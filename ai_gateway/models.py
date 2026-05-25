# models.py
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum

class GenerateRequest(BaseModel):
    user_id: str
    prompt: str
    request_id: Optional[str] = None
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    max_retries: int = Field(default=3, ge=1, le=10)

class GenerateResponse(BaseModel):
    status: str  # "success", "queued", "error"
    request_id: str
    message: str
    data: Optional[Any] = None

class ResultResponse(BaseModel):
    status: str  # "pending", "completed", "failed", "expired"
    request_id: str
    result: Optional[Any] = None
    completed_at: Optional[datetime] = None

class DLQEntry(BaseModel):
    request_id: str
    user_id: str
    prompt: str
    error: str
    failed_at: datetime
    retry_count: int
    max_retries: int
    
class CircuitStateResponse(BaseModel):
    name: str
    state: str
    failure_count: int
    last_failure_time: float
    time_since_last_failure: Optional[float]