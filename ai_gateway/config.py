# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    
    # Gemini Rate Limits (80% of actual quota for safety buffer)
    GEMINI_RPM_LIMIT: int = int(os.getenv("GEMINI_RPM_LIMIT", 8))  # 80% of 10
    GEMINI_TPM_LIMIT: int = int(os.getenv("GEMINI_TPM_LIMIT", 80000))  # 80% of 100k
    
    # Circuit Breaker Settings
    CIRCUIT_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", 5))  # 5 failures
    CIRCUIT_RECOVERY_TIMEOUT: int = int(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", 60))  # 60 seconds
    CIRCUIT_HALF_OPEN_MAX_CALLS: int = int(os.getenv("CIRCUIT_HALF_OPEN_MAX_CALLS", 3))
    
    # DLQ Settings
    DLQ_MAX_RETRIES: int = int(os.getenv("DLQ_MAX_RETRIES", 3))
    DLQ_RECOVERY_INTERVAL: int = int(os.getenv("DLQ_RECOVERY_INTERVAL", 5))  # seconds when idle
    DLQ_RESULT_TTL: int = int(os.getenv("DLQ_RESULT_TTL", 3600))  # 1 hour
    
    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    
    # Load Shedding
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", 100))

config = Config()