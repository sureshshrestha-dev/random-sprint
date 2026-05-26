from pymongo import AsyncMongoClient
import redis.asyncio as redis
import json
from typing import Optional

class Database:
    def __init__(self, uri="mongodb://localhost:27017", db_name="lega_setup_db"):
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
    def __init__(self, host='localhost', port=6379, db=0, max_connections=50):
        pool = redis.ConnectionPool(
            host=host, 
            port=port, 
            db=db, 
            max_connections=max_connections
        )
        self.redis = redis.Redis(connection_pool=pool)
    
    @property
    def client(self):
        return self.redis  # exposes raw redis.Redis

    async def get(self, key: str):
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: dict, expire: int = 3600):
        await self.redis.set(key, json.dumps(value), ex=expire)
    
    async def delete(self, key: str):
        await self.redis.delete(key)
    

async def get_db():
    db=Database()   
    return db

async def get_redis():
    redisclient = RedisClient()
    return redisclient