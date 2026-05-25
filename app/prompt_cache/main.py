import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# 1. The STATIC BLOCK (This is the heavy part that gets cached by Gemini)
SYSTEM_INSTRUCTIONS = """
You are the agent who takes responsibility for collection sales information based on user requests.

# REQUIRED USER INFORMATION FOR ACTIONS
- Delivery address: Required for physical versions (paperback/hardcover). For audiobooks/ebooks, use "not needed for xxx format".
- Do not ask for any other extra information since we only need contact and address.


# RESPONSE GUIDELINE
1. Response should be direct, to the point, and include only information of action result (success message of creation or error message of why it failed).
"""

# 2. The DYNAMIC BLOCK (The tail end that changes per request)
def generate_dynamic_prompt(contact, address, history, user_request):
    return f"""
{SYSTEM_INSTRUCTIONS}

# CUSTOMER INFORMATION 
(Use this available information gathered from past activity. If missing, prompt for it.)
Contact number: {contact}
Delivery address: {address}

## PREVIOUS CHAT LOGS
{history}

## CURRENT REQUEST
User: {user_request}
"""

# 3. Test Execution
async def test_caching():
    # Example for User A
    prompt_a = generate_dynamic_prompt(
        contact="123456789", 
        address="Kathmandu, Nepal", 
        history="User asked about return policy yesterday.",
        user_request="I want to buy a paperback book."
    )
    
    # Example for User B
    prompt_b = generate_dynamic_prompt(
        contact="987654321", 
        address="Lalitpur, Nepal", 
        history="User previously bought an ebook.",
        user_request="I need to cancel my order."
    )

    # Gemini 2.0 Flash automatically caches prefixes > 2048 tokens.
    # Even if your prompt is smaller, this structure is "Cache-Ready".
    for p in[prompt_a, prompt_b]:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=p
        )
        print(f"\nResponse: {response.text}")
        print(f"\n\nResponse: {response}")

import asyncio
asyncio.run(test_caching())