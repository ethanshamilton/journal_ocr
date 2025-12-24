from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

### context engineering

class ComprehensiveAnalysis(BaseModel):
    reasoning: str = Field(description="Provide reasoning that will help answer the question effectively.")
    analysis: str = Field(description="Provide your formal analysis.")
    excerpts: list[str] = Field(description="Propagate relevant excerpts from the entries.")

class Entry(BaseModel):
    date: str
    title: str
    text: str
    tags: list[str]
    embedding: list[float] | None

### API interfaces

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

class RetrievedDoc(BaseModel):
    entry: Entry
    distance: float | None

class ChatResponse(BaseModel):
    """used as response model to return results to frontend"""
    response: str
    docs: list[RetrievedDoc]
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

### thread management

class CreateThreadRequest(BaseModel):
    title: Optional[str] = None
    initial_message: Optional[str] = None

class CreateThreadResponse(BaseModel):
    thread_id: str
    created_at: datetime

class AddMessageRequest(BaseModel):
    role: str
    content: str

class UpdateThreadRequest(BaseModel):
    title: str

### ingestion pipeline

class UnprocessedDocs(BaseModel):
    to_transcribe: list[tuple[str, str]]
    to_embed: list[str]
