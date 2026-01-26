# Referenced Docs Metadata

Store metadata about which journal entries were referenced in each chat message. This enables future features like prioritizing frequently-referenced docs in retrieval.

## Current State

- Frontend manages `retrievedDocs` state in `ChatInterface.tsx`
- First message triggers retrieval, subsequent messages reuse those docs via `existing_docs`
- Backend `agentic_llm_flow` ignores `existing_docs` - always does fresh retrieval
- Frontend calls `addMessageToThread` to save messages separately from the chat response

## Desired State

- Fresh retrieval every turn (agentic flow already does this)
- Backend saves messages with doc metadata automatically
- Frontend has no doc state management
- Each message stores which docs were used, enabling future prioritization

## Implementation Plan

### 1. Backend: Add `doc_refs` to Messages Schema

**File:** `backend/src/core/lancedb_client.py`

Update the messages schema to include doc references:

```python
messages_schema = pa.schema([
    pa.field("message_id", pa.string()),
    pa.field("thread_id", pa.string()),
    pa.field("timestamp", pa.string()),
    pa.field("role", pa.string()),
    pa.field("content", pa.string()),
    pa.field("doc_refs", pa.list_(pa.string())),  # NEW: list of "date:title" refs
])
```

### 2. Backend: Update `save_message` to Accept `doc_refs`

**File:** `backend/src/core/lancedb_client.py`

```python
async def save_message(self, thread_id: str, role: str, content: str, doc_refs: list[str] = None) -> dict:
    """Save a message to a thread"""
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()

    message_doc = {
        "message_id": message_id,
        "thread_id": thread_id,
        "timestamp": now.isoformat(),
        "role": role,
        "content": content,
        "doc_refs": doc_refs or []
    }

    messages_table = await self.db.open_table("messages")
    await messages_table.add([message_doc])

    # update thread's updated_at
    await self.update_thread(thread_id, {})

    return message_doc
```

### 3. Backend: Have `agentic_llm_flow` Save Messages

**File:** `backend/src/backend/flows.py`

After generating the response, save both user and assistant messages if `thread_id` is provided:

```python
async def agentic_llm_flow(lance: AsyncLocalLanceDB, req: ChatRequest) -> ChatResponse:
    # ... existing agent loop code ...

    # synthesize final response
    llm_response = await agent_synthesizer(...)

    # build doc_refs from accumulated entries
    doc_refs = list(state.accumulated_entries.keys())  # already "date:title" format

    # save messages to thread if thread_id provided
    if req.thread_id:
        await lance.save_message(req.thread_id, "user", req.query)
        await lance.save_message(req.thread_id, "assistant", llm_response, doc_refs=doc_refs)

    # build response docs for frontend
    response_docs = []
    for entry in state.accumulated_entries.values():
        entry_for_response = entry.model_copy(update={"embedding": None})
        response_docs.append(RetrievedDoc(entry=entry_for_response, distance=None))

    return ChatResponse(response=llm_response, docs=response_docs, thread_id=req.thread_id)
```

### 4. Frontend: Remove Doc State Management

**File:** `ui/src/components/ChatInterface.tsx`

Remove:
- `retrievedDocs` state variable
- Conditional logic checking `retrievedDocs.length`
- Calls to `apiService.addMessageToThread`
- `existing_docs` from the request

Simplified `sendMessage`:

```typescript
const sendMessage = async () => {
  if (!inputText.trim()) return

  const query = inputText
  const userMessage: Message = {
    id: Date.now(),
    text: query,
    sender: 'user',
    timestamp: new Date()
  }

  setMessages(prev => [...prev, userMessage])
  setInputText('')
  setIsLoading(true)

  try {
    const response = await apiService.queryJournal({
      query,
      top_k: 5,
      provider: selectedModel.provider,
      model: selectedModel.model,
      thread_id: currentThreadId || "",
      message_history: isThreadSaved ? undefined : messages
    })

    const docs = response.docs.map((doc, i) => ({
      id: i + 1,
      title: doc.entry.title || `Entry ${i + 1}`,
      content: doc.entry.text || JSON.stringify(doc.entry)
    }))
    setDocuments(docs)

    const botMessage: Message = {
      id: Date.now() + 1,
      text: response.response,
      sender: 'assistant',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, botMessage])

    // No need to call addMessageToThread - backend handles it
  } catch (error) {
    // ... error handling
  } finally {
    setIsLoading(false)
  }
}
```

### 5. Backend: Update `ChatRequest` Model (Optional Cleanup)

**File:** `backend/src/core/models.py`

Remove `existing_docs` field since it's no longer used:

```python
class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    provider: str
    model: str
    thread_id: Optional[str]
    message_history: Optional[list[dict]] = None
    # existing_docs removed
```

## Future Enhancement: Doc Prioritization

With `doc_refs` stored per message, we can later implement:

1. **Query doc reference frequency:**
   ```python
   async def get_frequently_referenced_docs(thread_id: str) -> dict[str, int]:
       """Get doc_refs counts across all messages in a thread"""
       messages = await get_thread_messages(thread_id)
       ref_counts = {}
       for msg in messages:
           for ref in msg.get("doc_refs", []):
               ref_counts[ref] = ref_counts.get(ref, 0) + 1
       return ref_counts
   ```

2. **Boost frequently-referenced docs in retrieval:**
   - Pass ref_counts to agent tool selector
   - Weight vector search results by historical relevance
   - Pre-seed with frequently-referenced docs in addition to recent docs

## Migration Note

Existing messages tables won't have `doc_refs`. Options:
- Add column with default empty list
- Recreate table (loses history)
- Handle missing field gracefully in code
