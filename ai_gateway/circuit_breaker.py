# circuit_breaker.py
import asyncio
import time
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation - requests flow through
    OPEN = "open"          # Failing - requests fail fast
    HALF_OPEN = "half_open" # Testing - limited requests allowed

class CircuitBreaker:
    """
    Prevents cascading failures by stopping requests to a failing service.
    
    States:
    - CLOSED: Normal operation, counting failures
    - OPEN: Service is failing, fail fast for recovery_timeout seconds
    - HALF_OPEN: Test if service recovered with limited requests
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls_made = 0
        self._lock = asyncio.Lock()
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Raises:
            CircuitBreakerError: When circuit is open
            Exception: Propagates the original exception on failure
        """
        if not await self._allow_request():
            raise CircuitBreakerError(f"Circuit '{self.name}' is OPEN - failing fast")
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure(e)
            raise
    
    async def _allow_request(self) -> bool:
        """Check if a request should be allowed through"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info(f"Circuit '{self.name}' transitioning OPEN -> HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls_made = 0
                    return True
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                # Limit the number of test requests
                if self.half_open_calls_made < self.half_open_max_calls:
                    self.half_open_calls_made += 1
                    return True
                return False
            
            return False
    
    async def _record_success(self):
        """Record a successful call - may close the circuit"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit '{self.name}' transitioned HALF_OPEN -> CLOSED (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls_made = 0
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    async def _record_failure(self, error: Exception):
        """Record a failure - may open the circuit"""
        async with self._lock:
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit '{self.name}' HALF_OPEN test failed - reopening circuit")
                self.state = CircuitState.OPEN
                self.half_open_calls_made = 0
                
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    logger.error(f"Circuit '{self.name}' transitioned CLOSED -> OPEN after {self.failure_count} failures")
                    self.state = CircuitState.OPEN
                    self.failure_count = 0
    
    async def get_state(self) -> dict:
        """Get current circuit state for monitoring"""
        async with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "last_failure_time": self.last_failure_time,
                "time_since_last_failure": time.time() - self.last_failure_time if self.last_failure_time else None
            }

class CircuitBreakerError(Exception):
    pass