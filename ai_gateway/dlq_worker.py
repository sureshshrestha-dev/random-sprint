# dlq_worker.py
import asyncio
import json
import signal
from datetime import datetime
from typing import Optional
import logging

from core.database import redis_manager
from ai_gateway.gemini_client import ReliableGeminiClient
from ai_gateway.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DLQRecoveryWorker:
    """
    Background worker that retries failed requests from DLQ.
    Runs indefinitely with exponential backoff and priority queues.
    """
    
    def __init__(self, gemini_client: ReliableGeminiClient, redis_client):
        self.gemini = gemini_client
        self.redis = redis_client
        self.running = True
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Handle graceful shutdown"""
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
    
    def _shutdown(self, signum, frame):
        logger.info("Received shutdown signal - stopping DLQ worker")
        self.running = False
    
    async def run(self):
        """Main recovery loop - processes failed requests"""
        logger.info("DLQ Recovery Worker started")
        
        while self.running:
            try:
                # Try high priority queue first
                job = await self._get_next_job()
                
                if not job:
                    # No work - sleep briefly
                    await asyncio.sleep(config.DLQ_RECOVERY_INTERVAL)
                    continue
                
                # Process the job
                await self._process_job(job)
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(5)
        
        logger.info("DLQ Recovery Worker stopped")
    
    async def _get_next_job(self) -> Optional[dict]:
        """Get next job with priority: high > normal > poison (manual review)"""
        # Priority 1: High priority queue
        job_json = await self.redis.lpop("gemini:dlq:high")
        if job_json:
            return json.loads(job_json)
        
        # Priority 2: Normal queue
        job_json = await self.redis.lpop("gemini:dlq:normal")
        if job_json:
            return json.loads(job_json)
        
        return None
    
    async def _process_job(self, job: dict):
        """Retry a failed request with exponential backoff"""
        request_id = job['request_id']
        retry_count = job.get('retry_count', 0)
        max_retries = job.get('max_retries', config.DLQ_MAX_RETRIES)
        
        logger.info(f"Retrying {request_id} (attempt {retry_count + 1}/{max_retries})")
        
        # Attempt the Gemini call with retry logic
        success, result = await self.gemini._call_gemini_for_retry(
            job['prompt'], 
            retry_count
        )
        
        if success:
            # Success! Store result and celebrate
            await self.gemini._store_success(
                request_id, 
                job['user_id'], 
                result
            )
            logger.info(f"✅ DLQ recovery succeeded for {request_id}")
            return
        
        # Failed again - increment retry count
        job['retry_count'] = retry_count + 1
        job['last_error'] = result
        job['last_retry_at'] = datetime.now().isoformat()
        
        # Check if we've exhausted retries
        if job['retry_count'] >= max_retries:
            # Permanent failure - move to poison queue for manual inspection
            job['final_error'] = result
            job['abandoned_at'] = datetime.now().isoformat()
            
            await self.redis.rpush("gemini:poison", json.dumps(job))
            await self.redis.hincrby("gemini:metrics", "poison_count", 1)
            
            logger.error(f"💀 Request {request_id} permanently failed after {max_retries} retries")
            
            # Store failure result for user
            await self.redis.setex(
                f"result:{request_id}",
                config.DLQ_RESULT_TTL,
                json.dumps({
                    "user_id": job['user_id'],
                    "status": "failed",
                    "error": f"Permanent failure after {max_retries} retries: {result}",
                    "failed_at": datetime.now().isoformat()
                })
            )
            return
        
        # Re-queue for another retry
        await self._requeue_with_backoff(job)
    
    async def _requeue_with_backoff(self, job: dict):
        """Re-queue job with delay for exponential backoff"""
        retry_count = job['retry_count']
        
        # Exponential backoff: 10, 20, 40, 80, 160 seconds max
        delay = min(10 * (2 ** (retry_count - 1)), 300)
        
        logger.info(f"Re-queuing {job['request_id']} with {delay}s delay (retry {retry_count})")
        
        # Schedule for later using Redis sorted set (delayed queue)
        retry_at = datetime.now().timestamp() + delay
        
        # Store in delayed queue
        await self.redis.zadd(
            "gemini:dlq:delayed",
            {json.dumps(job): retry_at}
        )
        
        # Also have a separate worker to move from delayed to main queue
        await self._schedule_delayed_mover()
    
    async def _schedule_delayed_mover(self):
        """Background task to move delayed jobs back to main queue"""
        while True:
            now = datetime.now().timestamp()
            # Get all jobs ready for retry
            ready_jobs = await self.redis.zrangebyscore(
                "gemini:dlq:delayed", 
                0, 
                now
            )
            
            for job_json in ready_jobs:
                # Remove from delayed
                await self.redis.zrem("gemini:dlq:delayed", job_json)
                
                # Add back to appropriate priority queue
                job = json.loads(job_json)
                queue = "gemini:dlq:high" if job.get('max_retries', 0) > 5 else "gemini:dlq:normal"
                await self.redis.rpush(queue, job_json)
                logger.info(f"Moved delayed job {job['request_id']} back to {queue}")
            
            await asyncio.sleep(5)

# Standalone runner
async def main():
    """Run DLQ worker as standalone process"""
    # Connect to Redis
    redis = await redis_manager.connect(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB
    )
    
    # Initialize Gemini client
    gemini_client = ReliableGeminiClient(redis)
    
    # Start worker
    worker = DLQRecoveryWorker(gemini_client, redis)
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())