import asyncio
import json
from app.semanticcache.main import SemanticCache, gemini_async_client, QueryIntent, INTENT_TTL

# ============================================================
# Raw Products
# ============================================================

RAW_PRODUCTS = [
    {
        "code": "NASU2082",
        "name": "नायब सुब्बा प्रथम दोस्रो र तेस्रो पत्र (प्रशासन समूह)- nasu Prashasan 2082",
        "category": "Loksewa Nijamati",
        "price": 8000,
        "discount": 0,
        "description": "Comprehensive preparation for all papers of the Nasu Administration level.",
        "tags": ["Nasu full course prasasan", "nasu sabai paper", "nayab subba administration"],
        "additinal_informatin": {
            "teachers": "IQ- Kuber Adhikari Sir, GK - Manoj Sharma sir, Ajay Uprety Sir, Somraj Kafle sir, Aashaman Upadhya sir, Written - Badri P. Karki Sir, Bhimraj Uprety sir.",
            "qualification": "For Male:- age 18 to 35, for Female And Disabled people age 18 to 40, education: +2 pass.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
    {
        "code": "NAYAB1ST23",
        "name": "नायब सुब्बा (प्रथम पत्र) -Nasu 1st Paper 2082",
        "category": "Loksewa Nijamati",
        "price": 5000,
        "discount": 0,
        "description": "Focused preparation for the first paper of the Nayab Subba exam.",
        "tags": ["Nasu ko 1st paper", "nayab subba first", "nasu first paper"],
        "additinal_informatin": {
            "teachers": "IQ- Kuber Adhikari Sir, GK - Manoj Sharma sir, Ajay Uprety Sir, Somraj Kafle sir, Aashaman Upadhya sir.",
            "qualification": "For Male:- age 18 to 35, for Female And Disabled people age 18 to 40, education: +2 pass.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
    {
        "code": "NASU23-20822",
        "name": "नायब सुब्बा दोस्रो र तेस्रो पत्र (प्रशासन समूह)-Nasu 2nd&3rd 2082",
        "category": "Loksewa Nijamati",
        "price": 5000,
        "discount": 0,
        "description": "Targeted course for the second and third written papers of the Nasu administration group.",
        "tags": [],
        "additinal_informatin": {
            "teachers": "Badri P. Karki Sir, Bhimraj Uprety sir.",
            "qualification": "Age 18-35 (Male), 18-40 (Female/Disabled), +2 Pass.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
]


# ============================================================
# Token Counter — tracks real savings
# ============================================================

class TokenTracker:
    def __init__(self):
        self.total_tokens   = 0
        self.saved_tokens   = 0
        self.llm_calls      = 0
        self.cache_hits     = 0
        self.log: list[dict] = []

    def record_llm_call(self, question: str, tokens_used: int):
        self.total_tokens += tokens_used
        self.llm_calls    += 1
        self.log.append({
            "type":   "LLM_CALL",
            "question": question,
            "tokens": tokens_used,
        })

    def record_cache_hit(self, question: str, tokens_saved: int):
        self.saved_tokens += tokens_saved
        self.cache_hits   += 1
        self.log.append({
            "type":    "CACHE_HIT",
            "question": question,
            "saved":   tokens_saved,
        })

    def report(self):
        total = self.total_tokens + self.saved_tokens
        pct   = (self.saved_tokens / total * 100) if total else 0
        print("\n" + "=" * 60)
        print("TOKEN USAGE REPORT")
        print("=" * 60)
        print(f"  LLM calls made   : {self.llm_calls}")
        print(f"  Cache hits       : {self.cache_hits}")
        print(f"  Tokens used      : {self.total_tokens}")
        print(f"  Tokens saved     : {self.saved_tokens}")
        print(f"  Total would have : {total}")
        print(f"  Savings          : {pct:.1f}%")
        print("\nDetailed log:")
        for entry in self.log:
            if entry["type"] == "LLM_CALL":
                print(f"  💸 LLM  +{entry['tokens']:>4} tokens | {entry['question'][:55]}")
            else:
                print(f"  ✅ CACHE  0 tokens | saved {entry['saved']:>4} | {entry['question'][:45]}")


tracker = TokenTracker()


# ============================================================
# Product Cache — Redis layer (saves latency not tokens)
# ============================================================

class ProductCache:
    def __init__(self, redis_client, ttl: int = 86400):
        self.redis  = redis_client
        self.ttl    = ttl
        self.prefix = "product:"

    def _key(self, code: str) -> str:
        return f"{self.prefix}{code.upper().replace(' ', '_')}"

    async def get(self, code: str) -> dict | None:
        cached = await self.redis.get(self._key(code))
        if cached:
            return json.loads(cached)
        return None

    async def set(self, product: dict):
        key = self._key(product["code"])
        await self.redis.set(
            key,
            json.dumps(product, ensure_ascii=False),
            ex=self.ttl,
        )

    async def seed(self, products: list[dict]):
        for p in products:
            await self.set(p)
            print(f"  📦 Cached product: {p['code']}")


# ============================================================
# Answer Extractor — this is where tokens are spent
# ============================================================

async def extract_answer(product: dict, question: str) -> tuple[str, int]:
    """Returns (answer, estimated_tokens_used)."""

    product_json = json.dumps(product, ensure_ascii=False, indent=2)

    prompt = """You are an assistant for a Nepali Loksewa exam prep platform.
Answer the user's question using ONLY the product data below.
Be concise. Answer in the same language as the question.
If not found in data, say: त्यो जानकारी उपलब्ध छैन

Product Data:
{product}

Question: {question}
Answer:""".format(product=product_json, question=question)

    response = await gemini_async_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    answer = response.text.strip()

    # Estimate tokens: prompt chars/4 + answer chars/4 (rough approximation)
    estimated_tokens = (len(prompt) + len(answer)) // 4

    return answer, estimated_tokens


# ============================================================
# Agent2 — with semantic cache check BEFORE LLM call
# ============================================================

async def agent2(
    product_code: str,
    question: str,
    semantic_cache: SemanticCache,
    product_cache: ProductCache,
) -> str:

    print(f"\n  {'─'*54}")
    print(f"  Agent2 question : {question}")

    # ── Step 1: Semantic cache check — 0 tokens ──
    normalized = semantic_cache.normalize_query(question)
    embedding  = await semantic_cache.get_embedding(normalized)
    cached_answer = await semantic_cache.get_cached_response(
        embedding,
        threshold=0.88,
    )

    if cached_answer:
        # Estimate what this would have cost without cache
        product     = await product_cache.get(product_code)
        _, est_cost = await _estimate_cost(product, question) if product else (None, 300)
        tracker.record_cache_hit(question, est_cost)
        print(f"  ✅ Semantic Cache HIT — 0 tokens spent")
        print(f"  💬 Answer: {cached_answer[:120]}")
        return cached_answer

    # ── Step 2: Product cache (Redis) — saves latency ──
    product = await product_cache.get(product_code)
    if not product:
        return f"Product {product_code} not found."

    # ── Step 3: LLM extraction — costs tokens ──
    answer, tokens = await extract_answer(product, question)
    tracker.record_llm_call(question, tokens)
    print(f"  💸 LLM call — {tokens} tokens used")
    print(f"  💬 Answer: {answer[:120]}")

    # ── Step 4: Store in semantic cache — next user pays 0 ──
    ttl = INTENT_TTL[QueryIntent.PRODUCT_PRICE]
    await semantic_cache.store_exact_match(normalized, answer, product_key=product_code, ttl=ttl)
    await semantic_cache.store_response(normalized, embedding, answer, ttl=ttl)
    print(f"  💾 Answer cached for future users")

    return answer


async def _estimate_cost(product: dict, question: str) -> tuple[str, int]:
    """Dry-run cost estimate without storing."""
    product_json = json.dumps(product, ensure_ascii=False, indent=2)
    estimated    = (len(product_json) + len(question) + 200) // 4
    return "", estimated


# ============================================================
# Simulated Conversations
# Mimics 3 different users asking overlapping questions
# ============================================================

CONVERSATIONS = [
    # ── User 1 ── asks about full course
    ("NASU2082",    "nasu full course ko fee kati ho?"),
    ("NASU2082",    "kun teacher huncha nasu prashasan ma?"),
    ("NASU2082",    "class kati baje huncha nasu ko?"),

    # ── User 2 ── same product, rephrased questions (should hit cache)
    ("NASU2082",    "nasu prashasan ko price k ho?"),           # rephrased fee
    ("NASU2082",    "nasu ma ko le padhauncha?"),               # rephrased teacher
    ("NASU2082",    "nasu class ko time k ho?"),                # rephrased time

    # ── User 3 ── different product
    ("NAYAB1ST23",  "nasu 1st paper ko fee kati?"),
    ("NAYAB1ST23",  "first paper ma kun sir huncha?"),
    ("NAYAB1ST23",  "nayab subba 1st paper ko yogyata k ho?"),

    # ── User 4 ── same as user 3 rephrased (cache should save all)
    ("NAYAB1ST23",  "nasu pehilo patra ko mulya kati ho?"),     # rephrased fee
    ("NAYAB1ST23",  "1st paper teacher ko naam k ho?"),         # rephrased teacher

    # ── User 5 ── 2nd&3rd paper
    ("NASU23-20822","nasu 2nd 3rd paper ko price?"),
    ("NASU23-20822","dosro tesro patra ma ko sir huncha?"),
]


# ============================================================
# Main
# ============================================================

async def main():
    from core.database import get_redis

    redis_client  = await get_redis()
    raw_redis     = redis_client.redis

    product_cache = ProductCache(raw_redis, ttl=86400)
    sem_cache     = SemanticCache(
        raw_redis,
        similarity_threshold=0.85,
        ttl_seconds=86400,
    )

    await sem_cache.initialize()

    # Seed product cache
    print("\n" + "="*60)
    print("SEEDING PRODUCT CACHE")
    print("="*60)
    await product_cache.seed(RAW_PRODUCTS)

    # Run conversations
    print("\n" + "="*60)
    print("SIMULATING CONVERSATIONS (13 questions, 3 products)")
    print("="*60)

    for product_code, question in CONVERSATIONS:
        await agent2(product_code, question, sem_cache, product_cache)

    # Print token report
    tracker.report()

    await raw_redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())