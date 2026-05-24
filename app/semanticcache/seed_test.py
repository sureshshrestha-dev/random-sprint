import asyncio
import uuid
import numpy as np
from app.semanticcache.main import SemanticCache, gemini_async_client, gemini_client, QueryIntent, INTENT_TTL

# ============================================================
# Dummy Product Catalog (no hardcoding — driven by data)
# ============================================================

PRODUCTS = [
    {
        "name": "iPhone 16 Black",
        "price": 1234,
        "currency": "Rs",
        "variant": "iphone_16_black",
        "intent": QueryIntent.PRODUCT_PRICE,
    },
    {
        "name": "iPhone 16 Pro Blue",
        "price": 12345,
        "currency": "Rs",
        "variant": "iphone_16_pro_blue",
        "intent": QueryIntent.PRODUCT_PRICE,
    },
]

# ============================================================
# Seed: generate real embeddings + store in cache
# ============================================================

async def seed_products(cache: SemanticCache):
    print("\n" + "=" * 60)
    print("SEEDING PRODUCT DATA INTO CACHE")
    print("=" * 60)

    for product in PRODUCTS:
        # Build a natural language Q&A pair
        question = f"What is the price of {product['name']}?"
        answer   = f"The price of {product['name']} is {product['currency']} {product['price']}."

        normalized = cache.normalize_query(question)
        embedding  = await cache.get_embedding(normalized)
        ttl        = INTENT_TTL[product["intent"]]

        # Store in L1 exact cache (scoped by variant)
        await cache.store_exact_match(
            normalized,
            answer,
            product_key=product["variant"],
            ttl=ttl,
        )

        # Store in L2 semantic cache
        await cache.store_response(
            normalized,
            embedding,
            answer,
            ttl=ttl,
        )

        print(f"✅ Seeded: {product['name']} → {product['currency']} {product['price']}")

    print("Seeding complete.\n")


# ============================================================
# Test Queries
# ============================================================

TEST_QUERIES = [
    "What is the price of blue iPhone Pro?",       # should hit iPhone 16 Pro Blue
    "How much does iphone 16 black cost?",          # should hit iPhone 16 Black
    "iphone 15 black price",                        # should MISS — not in cache
    "Tell me the cost of iPhone 16 Pro in blue",   # semantic hit for Pro Blue
]


async def run_tests(cache: SemanticCache):
    print("\n" + "=" * 60)
    print("RUNNING TEST QUERIES")
    print("=" * 60)

    for query in TEST_QUERIES:
        print(f"\nQUERY : {query}")
        print("-" * 40)
        answer = await cache.ask(query)
        print(f"ANSWER: {answer}")


# ============================================================
# Main
# ============================================================

async def main():
    from core.database import get_redis

    redis_client = await get_redis()

    cache = SemanticCache(
        redis_client.redis,
        similarity_threshold=0.95,   # will be overridden per intent in ask()
        ttl_seconds=86400,
    )

    await cache.initialize()

    # Seed first
    await seed_products(cache)

    # Then test
    await run_tests(cache)

    await redis_client.redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())