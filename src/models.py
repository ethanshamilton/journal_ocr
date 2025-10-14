from typing import Optional
from datetime import datetime

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
    message_history: Optional[list[dict]] = None
    existing_docs: Optional[list[dict]] = None

class ChatResponse(BaseModel):
    response: str
    docs: list[tuple]
    thread_id: Optional[str]

class Thread(BaseModel):
    thread_id: str
    title: str
    tags: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    message_id: str
    thread_id: str
    timestamp: datetime
    role: str  # 'user' or 'assistant'
    content: str

class CreateThreadRequest(BaseModel):
    title: Optional[str] = None
    initial_message: Optional[str] = None

class CreateThreadResponse(BaseModel):
    thread_id: str
    created_at: datetime

class AddMessageRequest(BaseModel):
    role: str
    content: str
