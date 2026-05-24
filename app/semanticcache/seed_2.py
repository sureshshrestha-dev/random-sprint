import asyncio
import json
from app.semanticcache.main import SemanticCache, gemini_async_client, QueryIntent, INTENT_TTL

# ============================================================
# Raw Product Data — paste MongoDB docs directly
# ============================================================

RAW_PRODUCTS = [
    {
        "_id": {"$oid": "6979a46d86175a245e729a2b"},
        "name": "नायब सुब्बा प्रथम दोस्रो र तेस्रो पत्र (प्रशासन समूह)- nasu Prashasan 2082",
        "code": "NASU2082",
        "category": "Loksewa Nijamati",
        "price": 8000,
        "discount": 0,
        "package": "Nasu Prasasan",
        "description": "Comprehensive preparation for all papers of the Nasu Administration level.",
        "tags": ["Nasu full course prasasan", "nasu sabai paper", "nayab subba administration", "nsu prasasan", "prasasan nasu"],
        "additinal_informatin": {
            "teachers": "IQ- Kuber Adhikari Sir, GK - Manoj Sharma sir, Ajay Uprety Sir, Somraj Kafle sir, Aashaman Upadhya sir, Written - Badri P. Karki Sir, Bhimraj Uprety sir.",
            "qualification": "For Male:- age 18 to 35, for Female And Disabled people age 18 to 40, education: +2 pass.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
    {
        "_id": {"$oid": "6979a46d86175a245e729a2c"},
        "name": "नायब सुब्बा (प्रथम पत्र) -Nasu 1st Paper 2082",
        "code": "NAYAB1ST23",
        "category": "Loksewa Nijamati",
        "price": 5000,
        "discount": 0,
        "package": "Nasu Prasasan",
        "description": "Focused preparation for the first paper of the Nayab Subba exam.",
        "tags": ["Nasu ko 1st paper", "nayab subba first", "Nasu 1st Paper", "nasu first paper", "नायब सुब्बा (प्रथम पत्र)"],
        "additinal_informatin": {
            "teachers": "IQ- Kuber Adhikari Sir, GK - Manoj Sharma sir, Ajay Uprety Sir, Somraj Kafle sir, Aashaman Upadhya sir.",
            "qualification": "For Male:- age 18 to 35, for Female And Disabled people age 18 to 40, education: +2 pass.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
    {
        "_id": {"$oid": "6979a46d86175a245e729a2d"},
        "name": "नायब सुब्बा दोस्रो र तेस्रो पत्र (प्रशासन समूह)-Nasu 2nd&3rd 2082",
        "code": "NASU23-20822",
        "category": "Loksewa Nijamati",
        "price": 5000,
        "discount": 0,
        "package": "Nasu Prasasan",
        "description": "Targeted course for the second and third written papers of the Nasu administration group.",
        "tags": [],
        "additinal_informatin": {
            "teachers": "Badri P. Karki Sir, Bhimraj Uprety sir.",
            "qualification": "Age 18-35 (Male), 18-40 (Female/Disabled), +2 Pass in relevant subjects.",
            "vacancy_details": "Sanghiya Nasu vacancy will open on Poush's last wednesday.",
            "class_time": "Morning 5-8 am and evening 5:30-10 PM.",
        },
    },
]


# ============================================================
# Product Cache
# Caches full MongoDB doc in Redis — one fetch per product per day
# ============================================================

class ProductCache:

    def __init__(self, redis_client, ttl: int = 86400):
        self.redis  = redis_client
        self.ttl    = ttl
        self.prefix = "product:"

    def _key(self, code: str) -> str:
        return f"{self.prefix}{code.upper().replace(' ', '_')}"

    async def get(self, code: str) -> dict | None:
        key    = self._key(code)
        cached = await self.redis.get(key)
        if cached:
            print(f"  📦 Product Cache HIT  : {key}")
            return json.loads(cached)
        print(f"  📦 Product Cache MISS : {key}")
        return None

    async def set(self, product: dict):
        code = product.get("code", "")
        key  = self._key(code)
        doc  = {**product, "_id": str(product.get("_id", ""))}
        await self.redis.set(key, json.dumps(doc, ensure_ascii=False), ex=self.ttl)
        print(f"  📦 Product cached     : {key}")

    async def seed_from_raw(self, products: list[dict]):
        """Seed product cache directly from raw MongoDB docs."""
        for product in products:
            await self.set(product)


# ============================================================
# Answer Extractor
# LLM reads cached full doc and answers only what was asked
# ============================================================

async def extract_answer(product: dict, user_question: str) -> str:
    prompt = """You are an assistant for a Nepali Loksewa exam prep platform.
Answer the user's question using ONLY the product data below.
Be concise. Answer in the same language the user asked.
If the answer is not in the data, say "त्यो जानकारी उपलब्ध छैन" (information not available).

Product Data:
{product}

User Question: {question}

Answer:""".format(
        product=json.dumps(product, ensure_ascii=False, indent=2),
        question=user_question,
    )

    response = await gemini_async_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()


# ============================================================
# Product Identifier
# LLM identifies which product the user is asking about
# ============================================================

async def identify_product_code(user_question: str, products: list[dict]) -> str | None:
    catalog = "\n".join([
        f"- Code: {p['code']} | Name: {p['name']} | Tags: {', '.join(p.get('tags', []))}"
        for p in products
    ])

    prompt = """Identify which product the user is asking about from this catalog.
Respond with ONLY the product code (e.g. NASU2082), nothing else.
If unclear or not found, respond: UNKNOWN

Catalog:
{catalog}

User Question: {question}""".format(catalog=catalog, question=user_question)

    response = await gemini_async_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    code = response.text.strip().upper()
    return None if code == "UNKNOWN" else code


# ============================================================
# Agent Tool
# Simulates what your LLM agent tool does per user question
# ============================================================

async def agent_tool(
    user_question: str,
    product_cache: ProductCache,
    products: list[dict],
) -> str:

    print(f"\n{'='*60}")
    print(f"USER : {user_question}")
    print(f"{'-'*60}")

    # Step 1: Identify which product
    code = await identify_product_code(user_question, products)
    if not code:
        return "Sorry, I couldn't identify which course you're asking about."
    print(f"  🔍 Identified product : {code}")

    # Step 2: Get from product cache (no MongoDB in this demo)
    product = await product_cache.get(code)
    if not product:
        return f"Product '{code}' not found in cache."

    # Step 3: LLM extracts only what was asked
    answer = await extract_answer(product, user_question)
    print(f"  💬 Answer : {answer}")
    return answer


# ============================================================
# Test: simulate multi-turn conversation about same product
# Shows that MongoDB is only "fetched" once per product
# ============================================================

CONVERSATION = [
    # --- Round 1: about NASU2082 full course ---
    "nasu full course ko fee kati ho?",
    "kun teacher huncha nasu prashasan ma?",
    "class kati baje huncha?",
    "nasu 2082 ko yogyata k ho?",

    # --- Round 2: about 1st paper only ---
    "nasu 1st paper ko price kati?",
    "nayab subba first paper ma kun teacher padincha?",

    # --- Round 3: about 2nd & 3rd paper ---
    "nasu 2nd 3rd paper ko fee k ho?",
    "dosro tesro patra ma ko le padhauncha?",

    # --- Edge: ambiguous / cross-product ---
    "nasu ma badri sir ko class kati baje?",       # only in 2nd&3rd
    "kuber adhikari sir kun course ma huncha?",    # in full + 1st paper
    "kharidar ko fee kati ho?",                    # not in catalog → UNKNOWN
]


async def main():
    from core.database import get_redis

    redis_client = await get_redis()
    raw_redis    = redis_client.redis

    product_cache = ProductCache(raw_redis, ttl=86400)

    # ── Seed product cache from raw docs (replaces MongoDB fetch) ──
    print("\n" + "="*60)
    print("SEEDING PRODUCT CACHE (simulating MongoDB → Redis)")
    print("="*60)
    await product_cache.seed_from_raw(RAW_PRODUCTS)

    # ── Run simulated multi-turn conversation ──
    print("\n" + "="*60)
    print("SIMULATING MULTI-TURN AGENT CONVERSATION")
    print("="*60)

    for question in CONVERSATION:
        await agent_tool(question, product_cache, RAW_PRODUCTS)

    await raw_redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())