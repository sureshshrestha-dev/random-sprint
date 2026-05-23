"""
The "Write-Through" Cache Pattern

Currently, if your database update succeeds but your cache deletion fails, your system serves "stale" data forever.

    The Problem: Distributed systems are prone to partial failures.

    The Goal: Implement a Write-Through pattern (or "Cache Aside with TTL + Invalidation").

    Refactor: Create a DatabaseManager class that handles both the DB update and the Redis invalidation inside a try-except block, ensuring consistency.
"""
import json
from typing import Optional, Dict, Any

class DatabaseManager:
    def __init__(self, db, redis_client):
        self.db = db
        self.redis_client = redis_client
    
    def get_user(self, user_id):
        cached = self.redis_client.get(f"user:{user_id}")
        if cached:
            return json.loads(cached)
        user = self.db.find_one("users", {"_id": user_id})
        if not user:
            return "user Not found"
        user_dict = {
            "_id": str(user["_id"]),
            "username": user["username"],
            "role": user["role"]
        }
        self.redis_client.set(f"user:{user_id}", json.dumps(user_dict), ex=100)
        return user_dict
    
    def update_user_role(self, user_id, role):
        try:
            result = self.db.update_one("users", {"_id": user_id}, {"$set": {"role": role}})
            
            if result.modified_count == 0:
                return "not updated"
            self.redis_client.delete(f"user:{user_id}")
            return "update success"
            
        except Exception as e:
            print(f"Error updating user {user_id}: {e}")
            return "error updating"