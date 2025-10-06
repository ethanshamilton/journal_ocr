from typing import Optional

from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class LLMRequest(BaseModel):
    prompt: str
    provider: str
    model: str

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    provider: str
    model: str
    thread_id: Optional[str]

class ChatResponse(BaseModel):
    response: str
    docs: list[tuple]
    thread_id: Optional[str]
