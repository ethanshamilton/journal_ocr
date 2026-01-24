from dataclasses import dataclass, field
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

### agent loop state management

@dataclass
class SearchIteration:
    """Record of a single search iteration in the agent loop."""
    iteration: int
    tool: str
    reasoning: str
    query: Optional[str]
    results_count: int
    new_entries_added: int


@dataclass
class AgentSearchState:
    """Accumulates entries and tracks search history during agent loop."""
    accumulated_entries: dict[str, Entry] = field(default_factory=dict)  # keyed by date:title
    search_trace: list[SearchIteration] = field(default_factory=list)

    def _entry_id(self, entry: Entry) -> str:
        return f"{entry.date}:{entry.title}"

    def add_entry(self, entry: Entry) -> bool:
        """Add an entry if not already present. Returns True if added."""
        entry_id = self._entry_id(entry)
        if entry_id not in self.accumulated_entries:
            self.accumulated_entries[entry_id] = entry
            return True
        return False

    def add_entries(self, entries: list[Entry]) -> int:
        """Add multiple entries, returns count of new entries added."""
        added = 0
        for entry in entries:
            if self.add_entry(entry):
                added += 1
        return added

    def record_iteration(self, iteration: int, tool: str, reasoning: str,
                         query: Optional[str], results_count: int, new_entries: int):
        """Record a search iteration."""
        self.search_trace.append(SearchIteration(
            iteration=iteration,
            tool=tool,
            reasoning=reasoning,
            query=query,
            results_count=results_count,
            new_entries_added=new_entries
        ))

    def get_context_string(self) -> str:
        """Format accumulated entries for LLM context."""
        if not self.accumulated_entries:
            return "No entries retrieved yet."

        lines = []
        for i, entry in enumerate(self.accumulated_entries.values(), 1):
            lines.append(f"Entry {i}:")
            lines.append(f"  date: {entry.date}")
            lines.append(f"  title: {entry.title}")
            lines.append(f"  text: {entry.text}")
            lines.append("")
        return "\n".join(lines)

    def get_trace_string(self) -> str:
        """Format search trace for LLM context."""
        if not self.search_trace:
            return "No searches performed yet."

        lines = []
        for it in self.search_trace:
            lines.append(f"Iteration {it.iteration}: {it.tool}")
            lines.append(f"  Reasoning: {it.reasoning}")
            if it.query:
                lines.append(f"  Query: {it.query}")
            lines.append(f"  Results: {it.results_count} found, {it.new_entries_added} new")
            lines.append("")
        return "\n".join(lines)


### app status

class StatusResponse(BaseModel):
    status: str
