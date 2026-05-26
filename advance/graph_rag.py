import json
from typing import List
from google import genai
from pydantic import BaseModel, Field

class KnowledgeTriplet(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class DocumentEntities(BaseModel):
    entities: List[dict]
    triplets: List[KnowledgeTriplet]
    document_type: str

async def extract_graph_triplets(client: genai.Client, text: str) -> List[KnowledgeTriplet]:
    """Extract knowledge triplets from text using Gemini."""
    prompt = f"""Extract all knowledge triplets (Subject → Predicate → Object) from this legal text.

Text: {text[:30000]}

Return JSON with:
{{
    "entities": [{{"name": "...", "type": "...", "properties": {{}}}},
    "triplets": [{{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.95}}],
    "document_type": "contract|policy|regulation|guidance"
}}
"""
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": DocumentEntities,
        },
    )
    return DocumentEntities.model_validate_json(response.text).triplets