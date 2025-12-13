# Backend API Async Overhaul Plan

## Overview
Convert the FastAPI backend from pseudo-async (sync calls in async endpoints) to true async using native async clients for all I/O operations, plus add streaming support for chat responses.

## Current State
- Endpoints declared `async def` but call synchronous functions
- `time.sleep()` blocks event loop during rate limiting
- Global `lance = None` pattern for database access
- No streaming support

## Files to Modify

| File | Changes |
|------|---------|
| `src/lancedb_client.py` | Convert to `AsyncLocalLanceDB` using `lancedb.connect_async()` |
| `src/completions.py` | Use `AsyncOpenAI`, `AsyncAnthropic`, async Gemini client |
| `src/flows.py` | Convert to async functions with `await` |
| `src/api.py` | Proper async endpoints, dependency injection, streaming |
| `src/models.py` | Add streaming response models if needed |

---

## Phase 1: Async Database Client (`src/lancedb_client.py`)

Convert `LocalLanceDB` to `AsyncLocalLanceDB`:

```python
import lancedb

class AsyncLocalLanceDB:
    def __init__(self, path: str):
        self.path = path
        self.db: lancedb.AsyncConnection = None

    async def connect(self):
        self.db = await lancedb.connect_async(self.path)

    async def get_similar_entries(self, embedding: list[float], n: int = 5):
        table = await self.db.open_table("journal")
        results = await table.vector_search(embedding).limit(n).to_polars()
        return self.df_to_entries(results)

    # Convert all other methods to async...
```

**Key changes:**
- `lancedb.connect()` → `await lancedb.connect_async()`
- `db.open_table()` → `await db.open_table()`
- `table.search()` → `await table.vector_search()`
- `table.add()` → `await table.add()`
- `table.delete()` → `await table.delete()`

---

## Phase 2: Async LLM Clients (`src/completions.py`)

### 2.1 Initialize async clients

```python
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from google import genai

# Async clients
async_openai = AsyncOpenAI(api_key=OPENAI_API_KEY)
async_anthropic = AsyncAnthropic()
```

### 2.2 Convert functions to async

**`get_embedding()`:**
```python
async def get_embedding(text: str) -> list[float]:
    response = await google_client.aio.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents=text,
    )
    return response.embeddings[0].values
```

**`intent_classifier()`:**
```python
async def intent_classifier(query: str) -> str:
    client = instructor.from_openai(async_openai)
    response = await client.chat.completions.create(
        response_model=QueryIntent,
        messages=[...]
    )
    return response.intent
```

**`chat_response()` - with streaming:**
```python
async def chat_response_stream(request: ChatRequest, chat_history: list, entries_str: str):
    """Async generator for streaming responses"""
    client = instructor.from_anthropic(async_anthropic)

    async for partial in client.chat.completions.create_partial(
        response_model=DirectChatResponse,
        messages=chat_history,
        stream=True
    ):
        yield partial
```

**`comprehensive_analysis()`:**
```python
async def comprehensive_analysis(...) -> ComprehensiveAnalysis:
    # Replace time.sleep() with asyncio.sleep()
    await asyncio.sleep(delay)
```

**`transcribe_images()`:**
```python
async def transcribe_images(b64str_images: list[str], tags: str) -> str:
    tasks = [transcribe_single_image(img, tags) for img in b64str_images]
    transcriptions = await asyncio.gather(*tasks)
    return "".join(transcriptions)
```

---

## Phase 3: Async Flows (`src/flows.py`)

Convert orchestration functions:

```python
async def default_llm_flow(db: AsyncLocalLanceDB, request: ChatRequest) -> ChatResponse:
    # Get embedding
    embedding = await get_embedding(request.query)

    # Search similar entries
    entries = await db.get_similar_entries(embedding)

    # Get chat response
    response = await chat_response(request, [], entries_str)

    return ChatResponse(response=response)

async def default_llm_flow_stream(db: AsyncLocalLanceDB, request: ChatRequest):
    """Streaming version"""
    embedding = await get_embedding(request.query)
    entries = await db.get_similar_entries(embedding)

    async for chunk in chat_response_stream(request, [], entries_str):
        yield chunk
```

---

## Phase 4: Async API Endpoints (`src/api.py`)

### 4.1 Dependency injection for database

```python
from fastapi import Depends

async def get_db() -> AsyncLocalLanceDB:
    return app.state.db

@app.post("/journal_chat")
async def journal_chat(
    request: ChatRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> ChatResponse:
    return await default_llm_flow(db, request)
```

### 4.2 Streaming endpoint

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/journal_chat/stream")
async def journal_chat_stream(
    request: ChatRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
):
    async def generate():
        async for chunk in default_llm_flow_stream(db, request):
            yield f"data: {json.dumps(chunk.model_dump())}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 4.3 Update lifespan for async connection

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = AsyncLocalLanceDB("lance.journal-app")
    await db.connect()
    await db.startup_ingest()
    app.state.db = db
    yield
    # cleanup if needed
```

### 4.4 Convert all thread endpoints to async

```python
@app.post("/threads")
async def create_new_thread(
    req: CreateThreadRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> CreateThreadResponse:
    thread_doc = await db.create_thread(req.title, req.initial_message)
    return CreateThreadResponse(...)
```

---

## Phase 5: Testing

1. Add `pytest-asyncio` for async test support
2. Create async test fixtures for database
3. Test streaming endpoints with httpx async client

```python
# tests/test_api_async.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_journal_chat():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/journal_chat", json={...})
        assert response.status_code == 200
```

---

## Implementation Order

1. **lancedb_client.py** - Foundation layer, no dependencies on other changes
2. **completions.py** - LLM clients, can be tested independently
3. **flows.py** - Orchestration, depends on 1 & 2
4. **api.py** - Endpoints, depends on all above
5. **Tests** - Validate everything works

## Rollback Strategy

Keep sync versions as `_sync` suffixed functions during development so we can compare behavior and roll back if needed.

---

## Key Patterns

**Rate limiting:** Replace `time.sleep(delay)` with `await asyncio.sleep(delay)`

**Parallel operations:** Use `asyncio.gather()` for independent async calls

**Error handling:** Async exceptions propagate normally, wrap in try/except as needed

**Streaming:** Use `async for` with `yield` for SSE responses
