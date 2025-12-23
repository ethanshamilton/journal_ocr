# Implementation Plan: OneDrive Sync with Parallel Processing

## Overview
Add OneDrive sync capability that pulls new journal entries at startup, then launches backend/frontend servers with background transcription/embedding pipelines that don't block app availability.

---

## Architecture Design

### Startup Flow
```
./start.sh
├── 1. OneDrive Sync (blocking - pull new files only)
├── 2. Launch Backend (FastAPI) with modified lifespan:
│   ├── a. Load existing embedded data → app immediately usable
│   ├── b. Spawn background task: transcription pipeline
│   └── c. Spawn background task: embedding pipeline + incremental DB updates
├── 3. Launch Frontend (Vite dev server)
└── 4. Display startup status to user
```

### Background Processing Strategy
- **Backend starts immediately** with existing data loaded
- **Transcription/embedding run in background** using FastAPI BackgroundTasks or asyncio tasks
- **Database updates incrementally** as each entry is embedded
- **API endpoint** exposes processing status (files remaining, current progress)
- **Frontend polls** status endpoint and displays progress indicator

---

## Components to Create/Modify

### 1. **New: OneDrive Sync Module** (`src/onedrive_sync.py`)
**Purpose:** Pull new files from OneDrive to local disk

**Key Functions:**
- `sync_from_onedrive(onedrive_path: str, local_path: str) -> dict`
  - Compare files in OneDrive vs local using file paths/names
  - Copy only new files (not in local directory)
  - Return stats: `{"new_files": 5, "total_synced": 100}`
  
**Dependencies:**
- Uses standard `os`, `shutil`, `pathlib` for file operations
- No external OneDrive API needed (just local filesystem sync)

**Edge Cases:**
- Handle OneDrive sync folder not mounted/available
- Handle permission errors
- Verify OneDrive path exists before syncing

---

### 2. **New: Background Processing Coordinator** (`src/background_processing.py`)
**Purpose:** Manage async transcription/embedding with progress tracking

**Key Components:**
```python
class ProcessingStatus:
    is_processing: bool
    transcription_total: int
    transcription_completed: int
    embedding_total: int
    embedding_completed: int
    errors: list[str]

async def run_transcription_pipeline(root_dir: str, status: ProcessingStatus)
async def run_embedding_pipeline(root_dir: str, status: ProcessingStatus, db: AsyncLocalLanceDB)
```

**Features:**
- Wraps existing pipeline logic from `transcription_pipeline.py` and `embedding_pipeline.py`
- Updates shared `ProcessingStatus` object as files are processed
- Incremental database updates after each embedding completes
- Error handling that doesn't crash the entire pipeline

---

### 3. **Modified: FastAPI Backend** (`src/api.py`)

**Changes to `lifespan` function:**
```python
async def lifespan(app: FastAPI):
    # 1. Run OneDrive sync (blocking)
    sync_stats = sync_from_onedrive(ONEDRIVE_PATH, JOURNAL_PATH)
    print(f"Synced {sync_stats['new_files']} new files from OneDrive")
    
    # 2. Initialize database with existing data
    db = AsyncLocalLanceDB("lance.journal-app")
    await db.connect()
    await db.startup_ingest()  # Loads existing embedded entries
    app.state.db = db
    
    # 3. Create shared processing status
    app.state.processing_status = ProcessingStatus()
    
    # 4. Start background processing (non-blocking)
    asyncio.create_task(run_transcription_pipeline(JOURNAL_PATH, app.state.processing_status))
    asyncio.create_task(run_embedding_pipeline(JOURNAL_PATH, app.state.processing_status, db))
    
    yield
    print("shutting down")
```

**New API Endpoint:**
```python
@app.get("/processing_status")
async def get_processing_status() -> ProcessingStatusResponse:
    """Returns current transcription/embedding progress"""
    return app.state.processing_status
```

**Considerations:**
- Should `startup_ingest()` skip files that aren't embedded yet? (Yes - it should only load completed entries)
- Need to modify `load_notes_to_df()` to handle missing embeddings gracefully

---

### 4. **Modified: Database Client** (`src/lancedb_client.py`)

**New Method:**
```python
async def add_entry_incrementally(self, entry: Entry) -> None:
    """Add a single newly-embedded entry to the journal table"""
    # Convert entry to polars DataFrame row
    # Append to existing table (mode="append")
    # Update vector index if needed
```

**Modified: `startup_ingest()`**
- Currently uses `mode="overwrite"` for journal table
- Should continue doing this, but only with entries that have embeddings
- Log warning for entries without embeddings (they'll be added incrementally)

---

### 5. **Modified: Embedding Pipeline** (`src/embedding_pipeline.py`)

**Key Changes:**
- Remove standalone `main()` execution model
- Make core logic callable from `background_processing.py`
- Support incremental database updates instead of batch JSON file writes
- Still maintain JSON file as backup/cache

**Function Signature:**
```python
async def embed_entry(
    entry_path: str, 
    db: AsyncLocalLanceDB,
    status: ProcessingStatus
) -> None:
    """Embed a single entry and add it to the database"""
```

---

### 6. **Modified: Transcription Pipeline** (`src/transcription_pipeline.py`)

**Key Changes:**
- Similar refactoring as embedding pipeline
- Make async-compatible
- Support progress reporting via shared status object

---

### 7. **New: Unified Startup Script** (`start.sh`)

**Purpose:** Single command to start everything

```bash
#!/bin/bash
set -e

export PYTHONPATH=src

echo "🚀 Starting Journal OCR App"
echo ""

# Start backend (includes OneDrive sync + background processing)
echo "📡 Starting backend server..."
uv run uvicorn src.api:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend
echo "🎨 Starting frontend..."
cd ui && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ App started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   Background processing running..."
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

---

### 8. **Frontend: Processing Status Indicator**

**New Component:** `ProcessingIndicator.tsx`
- Polls `/processing_status` endpoint every 2 seconds
- Shows progress bar or badge when processing
- Displays: "Processing 5/20 entries..."
- Hides when complete

**Integration:**
- Add to `ChatInterface.tsx` or `App.tsx` as header banner
- Use simple state management with `useEffect` polling

---

## Environment Variables

**Add to `.env.example` and `.env`:**
```bash
# OneDrive Configuration
ONEDRIVE_PATH="/Users/username/OneDrive/Journal/Daily Pages"
# Note: JOURNAL_PATH will be the local sync destination
```

**Alternative approach:** 
- If `ONEDRIVE_PATH` is set, sync from there to `JOURNAL_PATH`
- If not set, assume `JOURNAL_PATH` is already up-to-date (skip sync)

---

## Error Handling & Edge Cases

### OneDrive Sync
- ❌ OneDrive path doesn't exist → Log warning, continue with local files only
- ❌ Permission denied → Log error, continue with local files
- ✅ No new files → Log "Already up to date", continue normally

### Background Processing
- ❌ Transcription fails for a file → Log error, continue with next file
- ❌ Embedding fails → Log error, mark file for retry, continue
- ✅ User queries while processing → Return results from available data only

### Database
- 🔄 Concurrent writes → LanceDB handles this, but test thoroughly
- 🔄 Re-indexing during writes → May need to rebuild index after batch completes

---

## Testing Strategy

### Unit Tests
- `test_onedrive_sync.py`: File comparison, new file detection
- `test_background_processing.py`: Status updates, error handling
- Update `test_completions.py`: Test individual pipeline functions

### Integration Tests
- Startup sequence with new files
- Background processing completion
- Incremental database updates
- Frontend status polling

### Manual Testing Checklist
1. ✅ Start app with no new files → Should start immediately
2. ✅ Start app with 10 new files → Should start, then process in background
3. ✅ Query app during processing → Should work with existing data
4. ✅ Frontend shows progress indicator
5. ✅ OneDrive path unavailable → Graceful degradation

---

## Implementation Order

### Phase 1: Core Infrastructure (No OneDrive yet)
1. Create `background_processing.py` with `ProcessingStatus` class
2. Modify `api.py` lifespan to support background tasks
3. Add `/processing_status` endpoint
4. Test with existing local files

### Phase 2: Incremental Database Updates
1. Add `add_entry_incrementally()` to `lancedb_client.py`
2. Modify embedding pipeline to update DB after each entry
3. Test concurrent access patterns

### Phase 3: OneDrive Sync
1. Create `onedrive_sync.py`
2. Add to startup sequence in `api.py`
3. Add environment variables
4. Test sync logic

### Phase 4: Frontend & Startup Script
1. Create `ProcessingIndicator.tsx`
2. Create unified `start.sh`
3. Update `AGENTS.md` with new startup command

### Phase 5: Polish & Documentation
1. Error handling improvements
2. Logging improvements
3. Update README.md
4. Performance testing

---

## Open Questions for User

1. **OneDrive Path Assumption:** Should I assume the OneDrive sync folder is already mounted at a filesystem path (like `/Users/username/OneDrive/`), or do you need actual OneDrive API integration?

2. **Progress Persistence:** If the app crashes during processing, should it remember what was already processed, or restart from scratch on next launch?

3. **UI Behavior:** Should queries against unembedded entries show a message like "This date hasn't been processed yet", or just silently exclude them?

4. **Performance:** Current pipelines are synchronous loops. Should I add actual parallel processing (multiple files at once) or keep it sequential but non-blocking?

5. **Startup Time:** With this approach, the backend will start in ~2-5 seconds (just loading existing data). Is this acceptable, or do you need sub-1-second startup?

---

## Estimated Complexity

- **OneDrive Sync:** Low (simple file copy logic)
- **Background Processing:** Medium (async coordination, status tracking)
- **Incremental DB Updates:** Medium (LanceDB append operations, index management)
- **Frontend Indicator:** Low (simple polling component)
- **Overall:** ~4-6 hours of focused development + testing

---

## Next Steps

Ready to begin implementation following the phase order outlined above.
