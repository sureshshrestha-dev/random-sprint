import os
from core.database import get_db, get_redis
import json
import uuid
import hashlib
import asyncio
from enum import Enum
from typing import Optional

import numpy as np

from redis.commands.search.field import TextField, VectorField

from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from google import genai
from dotenv import load_dotenv
load_dotenv()

# ============================================================
# Gemini Client
# ============================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY environment variable")

# Sync client (for sync context, if ever needed)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)

# ✅ FIX 1: Async client via .aio — required inside async functions
gemini_async_client = gemini_client.aio


# ============================================================
# Intent Classification
# ============================================================

class QueryIntent(str, Enum):
    PRODUCT_PRICE  = "product_price"
    PRODUCT_SPECS  = "product_specs"
    STOCK_STATUS   = "stock_status"
    RETURN_POLICY  = "return_policy"
    COMPARISON     = "comparison"
    GENERAL        = "general"
    PERSONAL       = "personal"


INTENT_TTL = {
    QueryIntent.PRODUCT_PRICE:  7200,    # 2 hours
    QueryIntent.PRODUCT_SPECS:  86400,   # 24 hours
    QueryIntent.STOCK_STATUS:   300,     # 5 minutes
    QueryIntent.RETURN_POLICY:  86400,   # 24 hours
    QueryIntent.COMPARISON:     3600,    # 1 hour
    QueryIntent.GENERAL:        3600,    # 1 hour
    QueryIntent.PERSONAL:       0,       # don't cache
}

INTENT_THRESHOLD = {
    QueryIntent.PRODUCT_PRICE:  0.99,   # strict — variants must match exactly
    QueryIntent.STOCK_STATUS:   0.99,   # strict
    QueryIntent.PRODUCT_SPECS:  0.95,
    QueryIntent.RETURN_POLICY:  0.90,
    QueryIntent.COMPARISON:     0.95,
    QueryIntent.GENERAL:        0.90,
    QueryIntent.PERSONAL:       0.99,
}


# ============================================================
# Semantic Cache
# ============================================================

class SemanticCache:
    """
    L1 Cache:
        Exact query match via SHA256

    L2 Cache:
        Semantic similarity using Redis Vector Search
    """

    def __init__(
        self,
        redis_client,
        *,
        index_name: str = "idx:semantic_cache",
        vector_dim: int = 3072,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 86400,
    ):
        self.redis = redis_client
        self.index_name = index_name
        self.vector_dim = vector_dim
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.prefix = "cache:"
        self.l1_prefix = "exact:"

    # ============================================================
    # Initialization
    # ============================================================

    async def initialize(self):
        """Create Redis vector index if it doesn't exist."""
        try:
            await self.redis.ft(self.index_name).info()
            print(f"Index already exists: {self.index_name}")

        except Exception:
            print(f"Creating index: {self.index_name}")

            schema = (
                TextField("question"),
                TextField("answer"),
                VectorField(
                    "embedding",
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.vector_dim,
                        "DISTANCE_METRIC": "COSINE",
                        "M": 16,
                        "EF_CONSTRUCTION": 200,
                    },
                ),
            )

            definition = IndexDefinition(
                prefix=[self.prefix],
                index_type=IndexType.HASH,
            )

            await self.redis.ft(self.index_name).create_index(
                fields=schema,
                definition=definition,
            )

            print("Redis vector index created")

    # ============================================================
    # Query Normalization
    # ============================================================

    @staticmethod
    def normalize_query(query: str) -> str:
        return " ".join(query.strip().lower().split())

    # ============================================================
    # Exact Match Hash
    # ============================================================

    @staticmethod
    def hash_query(query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()

    # ============================================================
    # Embeddings
    # ============================================================

    async def get_embedding(self, text: str) -> np.ndarray:
        response = await gemini_async_client.models.embed_content(
            model="gemini-embedding-2",  # ✅ add "models/" prefix
            contents=text,
        )
        embedding = response.embeddings[0].values
        return np.array(embedding, dtype=np.float32)

    # ============================================================
    # L1 Exact Cache
    # ============================================================

    async def get_exact_match(self, normalized_query: str, product_key: str = "general") -> Optional[str]:
        query_hash = self.hash_query(normalized_query)
        key = f"{self.l1_prefix}{product_key}:{query_hash}"
        cached = await self.redis.get(key)

        if cached:
            print("L1 Exact Cache HIT")
            return cached.decode("utf-8")

        return None

    async def store_exact_match(self, normalized_query: str, answer: str, product_key: str = "general", *, ttl: int = None):
        ttl = ttl if ttl is not None else self.ttl_seconds
        if ttl == 0:
            return
        query_hash = self.hash_query(normalized_query)
        key = f"{self.l1_prefix}{product_key}:{query_hash}"
        await self.redis.set(key, answer, ex=ttl)

    # ============================================================
    # Semantic Vector Search
    # ============================================================

    async def get_cached_response(self, query_embedding: np.ndarray, threshold: float = None) -> Optional[str]:
        threshold = threshold if threshold is not None else self.similarity_threshold
        query = "*=>[KNN 1 @embedding $vector AS distance]"

        redis_query = (
            Query(query)
            .return_fields("question", "answer", "distance")
            .sort_by("distance")
            .paging(0, 1)
            .dialect(2)
        )

        results = await self.redis.ft(self.index_name).search(
            redis_query,
            # ✅ FIX 3: Key must match the $param name in the query string exactly
            {"vector": query_embedding.tobytes()},
        )

        if not results.docs:
            print("Semantic Cache MISS")
            return None

        doc = results.docs[0]
        cosine_distance = float(doc.distance)
        similarity = 1 - cosine_distance

        print(f"Semantic Similarity: {similarity:.4f}")

        if similarity >= threshold:
            print("Semantic Cache HIT")
            return doc.answer

        print("Similarity below threshold")
        return None

    # ============================================================
    # Store Semantic Response
    # ============================================================

    async def store_response(
        self,
        question: str,
        query_embedding: np.ndarray,
        answer: str,
        *,
        ttl: int = None,
    ):
        ttl = ttl if ttl is not None else self.ttl_seconds
        if ttl == 0:
            return
        key = f"{self.prefix}{uuid.uuid4()}"

        payload = {
            "question": question,
            "answer": answer,
            "embedding": query_embedding.tobytes(),
        }

        await self.redis.hset(key, mapping=payload)
        await self.redis.expire(key, ttl)

        print(f"Stored response in semantic cache: {key}")

    # ============================================================
    # Gemini Generation
    # ============================================================

    async def generate_gemini_response(self, query: str) -> str:
        """Generate a response from Gemini (async)."""

        # ✅ FIX 4: Use gemini_async_client.models.generate_content (awaitable)
        response = await gemini_async_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
        )

        return response.text

    # ============================================================
    # Intent Classifier
    # ============================================================

    async def classify_intent(self, query: str) -> QueryIntent:
        prompt = """Classify this user query into exactly one category.
Respond with ONLY the category name, nothing else.

Categories:
- product_price     (asking about cost, price, discount, offer)
- product_specs     (asking about features, specs, dimensions, material)
- stock_status      (asking about availability, in stock, delivery time)
- return_policy     (asking about return, refund, warranty)
- comparison        (comparing two or more products)
- general           (general product question)
- personal          (order status, my account, my order)

Query: {query}""".format(query=query)

        response = await gemini_async_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip().lower()
        try:
            return QueryIntent(raw)
        except ValueError:
            return QueryIntent.GENERAL

    # ============================================================
    # Product Key Extractor
    # ============================================================

    async def extract_product_key(self, query: str) -> str:
        prompt = """Extract the specific product name and variant from this query.
Include color, size, model number — any differentiating attribute.
Respond with ONLY a short snake_case key, nothing else.
If no specific product, respond: general

Examples:
"what is the price of iphone 16 blue"  → iphone_16_blue
"iphone 16 black cost?"                → iphone_16_black
"iphone 16 pro blue price"             → iphone_16_pro_blue
"what is your return policy"           → general

Query: {query}""".format(query=query)

        response = await gemini_async_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip().lower()

    # ============================================================
    # Main Public API
    # ============================================================

    async def ask(self, query: str) -> str:
        """
        Main pipeline:
            1. Normalize query
            2. Classify intent + extract product key (parallel)
            3. Check L1 exact cache (scoped by product key)
            4. Embed query
            5. Semantic L2 search (with intent threshold)
            6. Gemini fallback
            7. Store result with intent-based TTL
        """

        normalized_query = self.normalize_query(query)

        # Classify intent + extract product key in parallel
        intent, product_key = await asyncio.gather(
            self.classify_intent(normalized_query),
            self.extract_product_key(normalized_query),
        )
        print(f"Intent: {intent} | Product Key: {product_key}")

        # Skip cache for personal queries
        if intent == QueryIntent.PERSONAL:
            print("Personal query — skipping cache")
            return await self.generate_gemini_response(query)

        # L1 exact cache (scoped by product key)
        exact = await self.get_exact_match(normalized_query, product_key)
        if exact:
            return exact

        # Embed
        embedding = await self.get_embedding(normalized_query)

        # L2 semantic cache with intent-based threshold
        threshold = INTENT_THRESHOLD[intent]
        semantic = await self.get_cached_response(embedding, threshold=threshold)
        if semantic:
            return semantic

        # Gemini fallback
        print("Calling Gemini API...")
        answer = await self.generate_gemini_response(query)

        # Store with intent-based TTL
        ttl = INTENT_TTL[intent]
        await self.store_exact_match(normalized_query, answer, product_key, ttl=ttl)
        await self.store_response(normalized_query, embedding, answer, ttl=ttl)

        return answer


# ============================================================
# Demo / Test
# ============================================================

async def main():
    redis_client = await get_redis()

    cache = SemanticCache(
        redis_client.redis,
        similarity_threshold=0.95,
        ttl_seconds=86400,
    )

    await cache.initialize()

    queries = [
        "What is machine learning?",
        "Explain machine learning.",
        "What is the capital of Nepal?",
        "Tell me Nepal's capital city.",
    ]

    for q in queries:
        print("\n" + "=" * 60)
        print(f"QUERY: {q}")
        answer = await cache.ask(q)
        print("\nANSWER:")
        print(answer[:300])

    
    await redis_client.redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())






# donot use plain redis-server installed (neede RediSearch module).
 
#     docker run -d \
#   --name redis-stack \
#   -p 6379:6379 \
#   -p 8001:8001 \
#   redis/redis-stack:latest