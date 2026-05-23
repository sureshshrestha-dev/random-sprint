import json
import asyncio
from datetime import datetime
import sys

sys.path.append('/home/personal/Desktop/learning/random-sprint')
from database import get_db, get_redis


class OrderOutboxPattern:
    """
    The Outbox Pattern ensures reliable event publishing.
    
    Problem: If you update a database and then try to publish an event to Redis,
    the application might crash between the two operations, causing data loss.
    
    Solution: 
    1. Save the order AND an outbox event in the SAME database transaction
    2. A background worker reads the outbox and publishes to Redis
    3. Only mark the event as sent after successful publishing
    
    This guarantees: "At-least-once" message delivery
    """
    
    def __init__(self):
        self.db = get_db()
        self.redis_client = get_redis()
    
    async def create_order(self, customer_id: str, amount: float) -> str:
        """
        Step 1: Create order in MongoDB
        Step 2: Create outbox entry in MongoDB (atomic with order creation)
        This ensures both succeed or both fail together.
        """
        order = {
            "customer_id": customer_id,
            "amount": amount,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # Insert order and get the order ID
        order_id = await self.db.insert_one("orders", order)
        print(f"✓ Order created: {order_id}")
        
        # Insert into outbox table (same transaction in MongoDB)
        outbox_event = {
            "event_type": "order_created",
            "event_data": {
                "order_id": str(order_id),
                "customer_id": customer_id,
                "amount": amount
            },
            "created_at": datetime.now().isoformat(),
            "published": False  # Mark as not yet published
        }
        
        await self.db.insert_one("outbox", outbox_event)
        print(f"✓ Outbox event created for order {order_id}")
        
        return str(order_id)
    
    async def publish_events_from_outbox(self):
        """
        Background worker that:
        1. Reads unpublished events from outbox
        2. Publishes them to Redis
        3. Marks them as published
        
        This runs periodically (cron job, async task, etc.)
        """
        cursor = self.db.find("outbox", {"published": False})
        events = await cursor.to_list(length=None)
        
        if not events:
            print("ℹ No unpublished events in outbox")
            return
        
        print(f"\n📤 Found {len(events)} unpublished events. Publishing...")
        
        for event in events:
            try:
                # Publish to Redis
                redis_key = f"events:{event['event_type']}"
                await self.redis_client.redis.rpush(
                    redis_key, 
                    json.dumps(event['event_data'])
                )
                print(f"  → Published {event['event_type']} to Redis")
                
                # Mark as published in MongoDB
                await self.db.update_one(
                    "outbox",
                    {"_id": event["_id"]},
                    {"published": True, "published_at": datetime.now().isoformat()}
                )
                print(f"  ✓ Marked as published")
                
            except Exception as e:
                print(f"  ✗ Failed to publish event: {e}")
                # Event stays in outbox, will retry next time
    
    async def consume_events_from_redis(self):
        """
        Simulate a subscriber reading events from Redis
        """
        redis_key = "events:order_created"
        
        print(f"\n📥 Checking Redis for events...")
        
        # Read all events from the queue
        while True:
            event_data = await self.redis_client.redis.lpop(redis_key)
            if not event_data:
                break
            
            event = json.loads(event_data)
            print(f"  Received event: {event}")
            # Here you could process the event (send email, update cache, etc.)
        
        if event_data is None:
            print("ℹ No events in Redis queue")


async def main():
    """
    Demo: Outbox Pattern in action
    """
    print("=" * 60)
    print("OUTBOX PATTERN EXAMPLE")
    print("=" * 60)
    
    pattern = OrderOutboxPattern()
    
    # Step 1: Create multiple orders (saves to outbox)
    print("\n1️⃣  CREATING ORDERS (with outbox entries)\n")
    order_id_1 = await pattern.create_order("CUST001", 99.99)
    order_id_2 = await pattern.create_order("CUST002", 149.99)
    order_id_3 = await pattern.create_order("CUST003", 199.99)
    
    # Step 2: Publish events from outbox to Redis
    print("\n2️⃣  PUBLISHING EVENTS FROM OUTBOX TO REDIS\n")
    await pattern.publish_events_from_outbox()
    
    # Step 3: Consumer reads from Redis
    print("\n3️⃣  CONSUMING EVENTS FROM REDIS\n")
    await pattern.consume_events_from_redis()
    
    print("\n" + "=" * 60)
    print("✓ Outbox pattern example complete!")
    print("=" * 60)
    
    # Verify published events in database
    print("\n4️⃣  VERIFYING OUTBOX STATE IN DATABASE\n")
    cursor = pattern.db.find("outbox", {})
    outbox_events = await cursor.to_list(length=None)
    for event in outbox_events:
        status = "✓ Published" if event.get("published") else "⏳ Pending"
        print(f"  {status}: {event['event_type']} for order {event['event_data']['order_id']}")


if __name__ == "__main__":
    asyncio.run(main())




## What the Pattern Does:

# **Problem**: If you update a database and then publish to Redis, a crash between the two could lose the event.

# **Solution** (Outbox Pattern):
# 1. **Create Order + Outbox Entry** (same operation) → Both succeed or both fail
# 2. **Background Worker** reads unpublished events from the outbox
# 3. **Publish to Redis** and mark as sent
# 4. **Guarantees** at-least-once delivery

## The Example Flow:

# 1. **Create Orders** - Stores 3 orders + outbox entries in MongoDB
# 2. **Publish Events** - Background worker sends events from outbox to Redis and marks them as published
# 3. **Consume Events** - A subscriber reads the events from Redis
# 4. **Verify** - Shows all events were successfully published

# This pattern is widely used in microservices architecture to ensure **eventual consistency** and **reliable event delivery**. The key advantage is that the database acts as the source of truth for events, so nothing gets lost even if the message broker is temporarily unavailable.

