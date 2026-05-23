from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
load_dotenv()

class MultiplicationTable(BaseModel):
    number: float = Field(description="The input number to generate table for")
    table: List[float] = Field(description="The multiplication table results")
    limit: int = Field(default=5, description="How many multiples to generate")

@tool
def generate_multiplication_table(number: float, limit: int = 5):
    """Generates a multiplication table for the given number up to the specified limit."""
    table = [number * i for i in range(1, limit + 1)]
    result={
        "number": number,
        "table": table
    }
    return result

llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=os.getenv("DEEPSEEK_API_KEY")
)

llm_with_tools = llm.bind_tools([generate_multiplication_table])

messages = [
    SystemMessage(content="You are a helpful assistant that generates multiplication tables. When a user asks for a table, use the generate_multiplication_table tool."),
    HumanMessage(content="Generate multiplication table for number 2 up to 5 multiples"),
]

response = llm_with_tools.invoke(messages)

if response.tool_calls:
    for tool_call in response.tool_calls:
        if tool_call["name"] == "generate_multiplication_table":
            args = tool_call["args"]
            number = args.get("number")
            limit = args.get("limit", 5)
            result = generate_multiplication_table(number, limit)
            print(f"Result: {result}")
            follow_up = llm.invoke([
                SystemMessage(content="Provide the multiplication table in a clear format"),
                HumanMessage(content=f"The multiplication table for {number} is: {result['table']}. Please present it nicely.")
            ])
            print(f"\nResponse:\n{follow_up.content}")

ai_msg = llm.invoke(messages)
ai_msg.content
ai_msg.response_metadata
ai_msg.usage_metadata
