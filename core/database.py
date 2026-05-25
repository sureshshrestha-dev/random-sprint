from pymongo import AsyncMongoClient
import redis.asyncio as redis
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri="mongodb://localhost:27017", db_name="eko_setup_db"):
        self.client = AsyncMongoClient(uri)
        self.db = self.client[db_name]

    async def insert_one(self, collection_name: str, document: dict):
        collection = self.db[collection_name]
        result = await collection.insert_one(document)
        return result.inserted_id

    async def find_one(self, collection_name: str, query: dict, projection: dict = None):
        collection = self.db[collection_name]
        if projection:
            document = await collection.find_one(query, projection)
        else:
            document = await collection.find_one(query)
        return document

    def find(self, collection_name: str, query: dict):
        collection = self.db[collection_name]
        return collection.find(query)

    async def update_one(self, collection_name: str, query: dict, update: dict):
        collection = self.db[collection_name]
        result = await collection.update_one(query, {'$set': update})
        return result.modified_count

    async def delete_one(self, collection_name: str, query: dict):
        collection = self.db[collection_name]
        result = await collection.delete_one(query)
        return result.deleted_count


class RedisClient:
    """Redis client with connection pooling"""
    def __init__(self, host='localhost', port=6379, db=0, max_connections=50):
        self._host = host
        self._port = port
        self._db = db
        self._max_connections = max_connections
        self._pool = None
        self._client = None
    
    async def connect(self):
        """Establish Redis connection pool"""
        self._pool = redis.ConnectionPool(
            host=self._host,
            port=self._port,
            db=self._db,
            max_connections=self._max_connections,
            decode_responses=True,
            socket_keepalive=True
        )
        self._client = redis.Redis(connection_pool=self._pool)
        # Test connection
        await self._client.ping()
        logger.info(f"Connected to Redis at {self._host}:{self._port}")
        return self._client
    
    @property
    def client(self):
        """Get raw redis client (must call connect first)"""
        if not self._client:
            raise RuntimeError("Redis not connected - call connect() first")
        return self._client

    async def get(self, key: str):
        """Get value by key, returns deserialized JSON"""
        data = await self._client.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: dict, expire: int = 3600):
        """Set key with JSON value and expiration"""
        await self._client.set(key, json.dumps(value), ex=expire)
    
    async def delete(self, key: str):
        """Delete key"""
        await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self._client.exists(key) > 0
    
    async def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        return await self._client.expire(key, seconds)
    
    # Additional methods for DLQ and other queue operations
    async def rpush(self, key: str, *values):
        """Push values to a list (right push)"""
        return await self._client.rpush(key, *values)
    
    async def lpop(self, key: str, count: int = 1):
        """Pop values from a list (left pop)"""
        return await self._client.lpop(key, count)
    
    async def zadd(self, key: str, mapping: dict):
        """Add members to a sorted set with scores"""
        return await self._client.zadd(key, mapping)
    
    async def zrangebyscore(self, key: str, min: float, max: float):
        """Get members from a sorted set within score range"""
        return await self._client.zrangebyscore(key, min, max)
    
    async def zrem(self, key: str, *members):
        """Remove members from a sorted set"""
        return await self._client.zrem(key, *members)
    
    async def setex(self, key: str, seconds: int, value: str):
        """Set a key with expiration (raw string)"""
        return await self._client.setex(key, seconds, value)
    
    async def hincrby(self, key: str, field: str, increment: int = 1):
        """Increment a hash field by the given amount"""
        return await self._client.hincrby(key, field, increment)
    
    async def publish(self, channel: str, message: str):
        """Publish a message to a channel"""
        return await self._client.publish(channel, message)
    
    async def hgetall(self, key: str):
        """Get all fields and values from a hash"""
        return await self._client.hgetall(key)
    
    async def llen(self, key: str):
        """Get the length of a list"""
        return await self._client.llen(key)
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            if self._pool:
                await self._pool.disconnect()
            logger.info("Redis connection closed")


class RedisManager:
    """Singleton Redis connection manager (alternative approach)"""
    _instance = None
    _client: Optional[RedisClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self, host: str = 'localhost', port: int = 6379, db: int = 0, max_connections: int = 50):
        """Establish Redis connection"""
        self._client = RedisClient(host, port, db, max_connections)
        await self._client.connect()
        return self._client
    
    async def get_client(self) -> RedisClient:
        """Get Redis client (must call connect first)"""
        if not self._client:
            raise RuntimeError("Redis not connected - call connect() first")
        return self._client
    
    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._client = None


redis_manager = RedisManager()


async def get_db():
    db = Database()   
    return db

async def get_redis():
    """Factory function to get a Redis client (non-singleton)"""
    redis_client = RedisClient()
    await redis_client.connect()
    return redis_client

async def get_redis_singleton():
    """Factory function to get the singleton Redis manager"""
    return redis_manager