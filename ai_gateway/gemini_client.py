# gemini_client.py
import asyncio
import json
import uuid
from datetime import datetime
from typing import Tuple, Optional
import logging

from aiolimiter import AsyncLimiter
from ai_gateway.circuit_breaker import CircuitBreaker, CircuitBreakerError
from ai_gateway.config import config
from ai_gateway.models import GenerateRequest

logger = logging.getLogger(__name__)

class ReliableGeminiClient:
    """Complete AI client with rate limiting, circuit breaker, and DLQ"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        # Token bucket for RPM (Requests Per Minute)
        self.rpm_limiter = AsyncLimiter(config.GEMINI_RPM_LIMIT, 60)
        # Token bucket for TPM (Tokens Per Minute) - approximate
        self.tpm_limiter = AsyncLimiter(config.GEMINI_TPM_LIMIT, 60)
        
        # Circuit breaker for Gemini
        self.circuit_breaker = CircuitBreaker(
            name="gemini_api",
            failure_threshold=config.CIRCUIT_FAILURE_THRESHOLD,
            recovery_timeout=config.CIRCUIT_RECOVERY_TIMEOUT,
            half_open_max_calls=config.CIRCUIT_HALF_OPEN_MAX_CALLS
        )
        
    async def generate_with_dlq(self, request: GenerateRequest) -> dict:
        """
        Main entry point for agents.
        Returns immediately - either success or queued for retry.
        """
        request_id = request.request_id or str(uuid.uuid4())
        
        # Check circuit breaker state first
        circuit_state = await self.circuit_breaker.get_state()
        if circuit_state["state"] == "open":
            # Circuit is open - queue immediately without trying
            await self._move_to_dlq(
                request_id=request_id,
                user_id=request.user_id,
                prompt=request.prompt,
                error_msg=f"Circuit breaker OPEN (last failure: {circuit_state['time_since_last_failure']:.0f}s ago)",
                max_retries=request.max_retries
            )
            return {
                "status": "queued",
                "request_id": request_id,
                "message": f"AI service temporarily unavailable - request queued for retry"
            }
        
        # Try to call Gemini with circuit breaker protection
        try:
            result = await self.circuit_breaker.call(
                self._call_gemini_with_limits,
                request.prompt
            )
            
            # Success!
            await self._store_success(request_id, request.user_id, result)
            await self._record_metrics(success=True)
            
            return {
                "status": "success",
                "request_id": request_id,
                "message": "Request completed successfully",
                "data": result
            }
            
        except CircuitBreakerError as e:
            # Circuit is open - queue the request
            await self._move_to_dlq(
                request_id=request_id,
                user_id=request.user_id,
                prompt=request.prompt,
                error_msg=str(e),
                max_retries=request.max_retries
            )
            await self._record_metrics(success=False, error="circuit_open")
            
            return {
                "status": "queued",
                "request_id": request_id,
                "message": "AI service experiencing issues - request queued for retry"
            }
            
        except Exception as e:
            # Other failure (rate limit, network, etc.)
            await self._move_to_dlq(
                request_id=request_id,
                user_id=request.user_id,
                prompt=request.prompt,
                error_msg=str(e),
                max_retries=request.max_retries
            )
            await self._record_metrics(success=False, error=str(e)[:50])
            
            return {
                "status": "queued",
                "request_id": request_id,
                "message": f"Request queued for retry due to: {str(e)[:100]}"
            }
    
    async def _call_gemini_with_limits(self, prompt: str) -> str:
        """
        Actual Gemini API call with rate limiting.
        This is the only function that touches the external API.
        """
        # Apply rate limits (both RPM and TPM)
        async with self.rpm_limiter:
            async with self.tpm_limiter:
                # Simulate token counting (approx)
                estimated_tokens = len(prompt.split()) * 1.3
                logger.info(f"Calling Gemini (estimated tokens: {estimated_tokens})")
                
                # TODO: Replace with actual Gemini API call
                # from google import genai
                # client = genai.Client(api_key=config.GEMINI_API_KEY)
                # response = await client.aio.models.generate_content(
                #     model=config.GEMINI_MODEL,
                #     contents=prompt
                # )
                # return response.text
                
                # Mock implementation for testing
                await asyncio.sleep(0.5)  # Simulate API latency
                
                # Simulate random failures for testing (10% failure rate)
                import random
                if random.random() < 0.1:
                    if random.random() < 0.5:
                        raise Exception("429: Rate limit exceeded")
                    else:
                        raise Exception("503: Gemini service unavailable")
                
                return f"Gemini response to: {prompt[:100]}..."
    
    async def _call_gemini_for_retry(self, prompt: str, retry_count: int) -> Tuple[bool, str]:
        """
        Special version for DLQ retries with exponential backoff.
        Returns (success, result_or_error)
        """
        try:
            # Exponential backoff before retry
            backoff_seconds = min(2 ** retry_count, 60)  # 1, 2, 4, 8, 16, 32, 60 max
            if retry_count > 0:
                logger.info(f"Backing off {backoff_seconds}s before retry {retry_count}")
                await asyncio.sleep(backoff_seconds)
            
            result = await self._call_gemini_with_limits(prompt)
            return (True, result)
            
        except Exception as e:
            return (False, str(e))
    
    async def _move_to_dlq(self, request_id: str, user_id: str, prompt: str, error_msg: str, max_retries: int):
        """Store failed request in persistent DLQ"""
        dlq_entry = {
            "request_id": request_id,
            "user_id": user_id,
            "prompt": prompt,
            "error": error_msg,
            "failed_at": datetime.now().isoformat(),
            "retry_count": 0,
            "max_retries": max_retries
        }
        
        # Use priority-based queues
        queue_name = "gemini:dlq:high" if max_retries > 5 else "gemini:dlq:normal"
        
        await self.redis.rpush(queue_name, json.dumps(dlq_entry))
        logger.warning(f"Moved request {request_id} to DLQ ({queue_name}): {error_msg[:100]}")
    
    async def _store_success(self, request_id: str, user_id: str, result: str):
        """Store successful result for later retrieval"""
        await self.redis.setex(
            f"result:{request_id}",
            config.DLQ_RESULT_TTL,
            json.dumps({
                "user_id": user_id,
                "result": result,
                "completed_at": datetime.now().isoformat()
            })
        )
        # Notify via pub/sub
        await self.redis.publish(f"user:{user_id}:results", request_id)
        logger.info(f"Stored result for {request_id}")
    
    async def _record_metrics(self, success: bool, error: str = None):
        """Track metrics for monitoring"""
        metrics_key = "gemini:metrics"
        
        if success:
            await self.redis.hincrby(metrics_key, "success_count", 1)
        else:
            await self.redis.hincrby(metrics_key, "failure_count", 1)
            if error:
                await self.redis.hincrby(metrics_key, f"error:{error[:20]}", 1)
    
    async def get_metrics(self) -> dict:
        """Get current metrics"""
        metrics = await self.redis.hgetall("gemini:metrics")
        circuit_state = await self.circuit_breaker.get_state()
        
        return {
            "metrics": metrics,
            "circuit_breaker": circuit_state,
            "dlq_lengths": {
                "high": await self.redis.llen("gemini:dlq:high"),
                "normal": await self.redis.llen("gemini:dlq:normal"),
                "poison": await self.redis.llen("gemini:poison")
            }
        }