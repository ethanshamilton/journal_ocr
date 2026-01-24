# Agentic LLM Search Loop Implementation Plan

## Overview
Implement an iterative LLM flow where the model can loop over queries, call multiple search tools, and synthesize the best possible response.

## Architecture

```
User Query
    ↓
┌─────────────────────────────────────┐
│         AGENTIC LOOP                │
│  ┌─────────────────────────────┐    │
│  │  AgentToolSelector (LLM)    │    │
│  │  - Chooses tool or DONE     │    │
│  │  - Provides reasoning       │    │
│  └──────────────┬──────────────┘    │
│                 ↓                   │
│  ┌─────────────────────────────┐    │
│  │  Execute Selected Tool      │    │
│  │  - VECTOR_SEARCH            │    │
│  │  - RECENT_ENTRIES           │    │
│  │  - DATE_RANGE_SEARCH        │    │
│  └──────────────┬──────────────┘    │
│                 ↓                   │
│  ┌─────────────────────────────┐    │
│  │  Accumulate Context         │    │
│  │  - Deduplicate entries      │    │
│  │  - Track search trace       │    │
│  └──────────────┬──────────────┘    │
│                 ↓                   │
│        (loop until DONE)            │
└─────────────────────────────────────┘
    ↓
AgentSynthesizer (LLM)
    ↓
ChatResponse
```

## Files to Modify

### 1. `backend/src/core/baml_src/completions.baml`
Add new BAML definitions:

```baml
enum SearchToolType {
  VECTOR_SEARCH
  RECENT_ENTRIES
  DATE_RANGE_SEARCH
  DONE
}

class SearchToolCall {
  tool SearchToolType
  reasoning string
  query string?           // For VECTOR_SEARCH
  start_date string?      // For DATE_RANGE_SEARCH
  end_date string?        // For DATE_RANGE_SEARCH
  limit int?              // Optional result limit
}

function AgentToolSelector(
  user_query: string,
  accumulated_context: string,
  iteration: int,
  max_iterations: int
) -> SearchToolCall

function AgentSynthesizer(
  user_query: string,
  chat_history: string,
  accumulated_context: string,
  search_trace: string
) -> string
```

### 2. `backend/src/core/models.py`
Add state management classes:

```python
@dataclass
class RetrievedEntry:
    entry_id: str
    date: str
    title: str
    text: str
    retrieval_method: str
    relevance_score: Optional[float] = None

@dataclass
class SearchIteration:
    iteration: int
    tool: str
    reasoning: str
    query: Optional[str]
    results_count: int
    new_entries_added: int

@dataclass
class AgentSearchState:
    accumulated_entries: dict[str, RetrievedEntry]
    search_trace: list[SearchIteration]
    # Methods: add_entry(), get_context_string(), get_trace_string()
```

Update `ChatRequest` with optional fields:
- `use_agent: bool = False`
- `max_iterations: int = 5`

### 3. `backend/src/backend/completions.py`
Add wrapper functions:
- `agent_tool_selector()` - calls BAML AgentToolSelector
- `agent_synthesizer()` - calls BAML AgentSynthesizer with ClientRegistry

### 4. `backend/src/backend/flows.py`
Add main flow function:

```python
async def agentic_llm_flow(lance: AsyncLocalLanceDB, req: ChatRequest) -> ChatResponse:
    state = AgentSearchState()

    for iteration in range(1, MAX_ITERATIONS + 1):
        tool_call = await agent_tool_selector(...)

        if tool_call.tool == DONE:
            break

        entries = await _execute_tool(lance, tool_call)
        state.add_entries(entries)

    response = await agent_synthesizer(...)
    return ChatResponse(...)

async def _execute_tool(lance, tool_call) -> list[Entry]:
    match tool_call.tool:
        case VECTOR_SEARCH: ...
        case RECENT_ENTRIES: ...
        case DATE_RANGE_SEARCH: ...
```

### 5. `backend/src/backend/api.py`
Add new endpoint:

```python
@app.post("/journal_chat_agent")
async def journal_chat_agent(
    request: ChatRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> ChatResponse:
    return await agentic_llm_flow(db, request)
```

## Key Design Decisions

1. **Tool selector returns class with reasoning** - Better for debugging/transparency than enum alone
2. **Entry deduplication by hash(date+title)** - Prevents duplicate context across searches
3. **Token-aware context truncation** - Prevents exceeding model limits
4. **Search trace passed to synthesizer** - Provides transparency about retrieval process
5. **Max iterations cap (default 5)** - Prevents runaway loops
6. **Fallback on errors** - If tool selector fails, fall back to simple vector search

## Available Search Tools (from lancedb_client.py)

| Tool | Method | Parameters |
|------|--------|------------|
| VECTOR_SEARCH | `get_similar_entries()` | embedding, n |
| RECENT_ENTRIES | `get_recent_entries()` | n |
| DATE_RANGE_SEARCH | `get_entries_by_date_range()` | start_date, end_date |

## Verification

1. **Unit tests**: Test `AgentSearchState` deduplication and token limits
2. **Integration test**: Mock LanceDB, verify tool dispatch
3. **Manual test**: Query like "What have I been stressed about lately vs last year?" should trigger multiple searches
4. **Run BAML generate**: `baml-cli generate` after modifying completions.baml
