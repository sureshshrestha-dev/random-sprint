import asyncio
import random
import string
import sys

sys.path.append('/home/personal/Desktop/learning/random-sprint')

from database import get_db

def create_random_user(index):
    return {
        "name": ''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 7))),
        "empi_id": f"EMP{index:05d}",
        "age": random.randint(20, 60),
        "department": random.choice(["python", "java", "c++"])
    }

data = [create_random_user(i) for i in range(1000)]

async def insert_random_users():
    db = get_db()
    await db.db["testt"].create_index("empi_id")
    tasks = [db.insert_one("testt", user) for user in data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def find_user_by_empi_id(empi_id):
    db = get_db()
    user = await db.find_one("testt", {"empi_id": empi_id})
    
    cursor = db.find("testt", {"empi_id": empi_id})
    stats = await cursor.explain()
    
    print(f"Total docs examined: {stats['executionStats']['totalDocsExamined']}")
    print(f"Total docs returned: {stats['executionStats']['nReturned']}")
    print(f"Stage: {stats['queryPlanner']['winningPlan']['stage']}")
    
    return user

async def main():
    insert_results = await insert_random_users()
    await find_user_by_empi_id("EMP00013")
    print(f"Inserted {len(insert_results)} users.")

if __name__ == "__main__":
    asyncio.run(main())

# doff before index
# Total docs examined: 6001
# Total docs returned: 7
# Stage: COLLSCAN
# Inserted 1000 users.

# after index
# Total docs examined: 8
# Total docs returned: 8
# Stage: FETCH
# Inserted 1000 users.
# (random-sprint) personal@suresh-Nitro-NL16-71G:~/Desktop/learning/random-sprint$ 
