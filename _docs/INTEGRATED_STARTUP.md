# Implementation Plan: Batch API Ingestion Pipeline

## Overview

Replace synchronous per-file API calls with batch jobs, consolidating transcription and embedding into a single ingestion pipeline that runs on app startup.

- **OpenAI Batch API** for transcription (vision/OCR) - 50% cost savings
- **Google Batch Embedding** for embeddings (native batch support)
- **Single pipeline** with state persistence for crash recovery

---

## Architecture

```
./start.sh
├── 1. OneDrive Sync (blocking)
├── 2. Launch Backend with modified lifespan:
│   ├── a. Load existing embedded data → app immediately usable
│   ├── b. Check for in-progress batch jobs (resume if found)
│   └── c. Spawn background task: BatchIngestionPipeline
│       ├── Phase 1: Collect files needing transcription/embedding
│       ├── Phase 2: Submit OpenAI batch job for transcription
│       ├── Phase 3: Poll for transcription completion (every 30s)
│       ├── Phase 4: Write transcriptions to markdown files
│       ├── Phase 5: Batch embed via Google API
│       └── Phase 6: Ingest embeddings to LanceDB
├── 3. Launch Frontend
└── 4. Display status
```

---

## Task List

### Phase 1: OpenAI Batch Transcription Client

- [ ] **1.1** Create `pipeline/openai_batch.py`
  - [ ] `prepare_transcription_jsonl(files: list[str], tags: str) -> str`
    - Encode images to base64
    - Write JSONL file with chat completion requests
    - Use `custom_id` format: `{filename}-page-{n}`
    - Return path to JSONL file
  - [ ] `upload_batch_file(jsonl_path: str) -> str`
    - Upload JSONL to OpenAI Files API
    - Return file_id
  - [ ] `create_batch_job(file_id: str) -> str`
    - Create batch job with endpoint `/v1/chat/completions`
    - Return batch_id
  - [ ] `poll_batch_status(batch_id: str) -> BatchStatus`
    - Return status: `in_progress`, `completed`, `failed`, `expired`
  - [ ] `download_batch_results(batch_id: str) -> dict[str, str]`
    - Download output file
    - Parse JSONL results
    - Return `{custom_id: transcription_text}`

- [ ] **1.2** Add batch settings to `core/settings.py`
  - [ ] `batch_state_path: str` - path to state JSON file
  - [ ] `batch_poll_interval: int = 30` - seconds between polls

### Phase 2: Google Batch Embedding Client

- [ ] **2.1** Create `pipeline/google_batch.py`
  - [ ] `batch_embed_texts(texts: dict[str, str]) -> dict[str, list[float]]`
    - Takes `{file_path: transcription_text}`
    - Calls `embed_content` with list of contents
    - Returns `{file_path: embedding_vector}`
  - [ ] Handle chunking if needed (Gemini may have limits per request)

### Phase 3: Batch Ingestion Pipeline Coordinator

- [ ] **3.1** Create `pipeline/batch_ingestion.py`
  - [ ] Define `BatchJobState` dataclass:
    ```python
    @dataclass
    class BatchJobState:
        phase: Literal["idle", "transcribing", "embedding", "complete"]
        transcription_batch_id: str | None
        files_to_transcribe: list[str]
        files_to_embed: list[str]
        errors: list[str]
        last_updated: str
    ```
  - [ ] `load_state() -> BatchJobState` - load from JSON or create fresh
  - [ ] `save_state(state: BatchJobState)` - persist to JSON
  - [ ] `clear_state()` - delete state file when complete

- [ ] **3.2** Implement `BatchIngestionPipeline` class
  - [ ] `async run()` - main entry point
    - Load state, resume or start fresh
    - Run through phases sequentially
    - Update ProcessingStatus for frontend
  - [ ] `async run_transcription_phase(state)`
    - If batch_id exists, poll for completion
    - Otherwise, prepare and submit new batch
    - On completion, write transcriptions to files
    - Update file frontmatter: `transcription: "True"`
    - Log any failed files (don't retry)
  - [ ] `async run_embedding_phase(state)`
    - Collect files with `transcription: True` but `embedding: False`
    - Batch embed via Google API
    - Update file frontmatter: `embedding: "True"`
    - Log any failed files (don't retry)
  - [ ] `async run_ingest_phase(state)`
    - Ingest newly embedded entries to LanceDB
    - Clear state file on success

- [ ] **3.3** Create `ProcessingStatus` class for frontend polling
  ```python
  @dataclass
  class ProcessingStatus:
      phase: str  # idle, transcribing, embedding, ingesting, complete
      transcription_total: int
      transcription_completed: int
      embedding_total: int
      embedding_completed: int
      errors: list[str]
  ```

### Phase 4: Backend Integration

- [ ] **4.1** Modify `backend/api.py` lifespan
  - [ ] Initialize `ProcessingStatus` in `app.state`
  - [ ] Create and run `BatchIngestionPipeline` as background task
  - [ ] Pipeline updates `app.state.processing_status` as it progresses

- [ ] **4.2** Add `/processing_status` endpoint
  ```python
  @app.get("/processing_status")
  async def get_processing_status():
      return app.state.processing_status
  ```

- [ ] **4.3** Modify `lancedb_client.py`
  - [ ] Ensure `startup_ingest()` only loads entries with `embedding: True`
  - [ ] Add `add_entries_batch()` method for bulk insertion after embedding

### Phase 5: Frontend Status Indicator

- [ ] **5.1** Create `ProcessingIndicator.tsx` component
  - [ ] Poll `/processing_status` every 2 seconds while processing
  - [ ] Display current phase and progress
  - [ ] Hide when complete

- [ ] **5.2** Integrate into `App.tsx` or header

### Phase 6: Cleanup & Testing

- [ ] **6.1** Update `pipeline/__init__.py` exports
- [ ] **6.2** Remove or deprecate old pipeline files
  - `transcription_pipeline.py` - keep for manual CLI use or remove
  - `embedding_pipeline.py` - keep for manual CLI use or remove
- [ ] **6.3** Keep `transcription.py` utilities (encoding, frontmatter updates)
- [ ] **6.4** Test end-to-end flow with sample data
- [ ] **6.5** Test crash recovery (kill app mid-batch, restart)
- [ ] **6.6** Update `AGENTS.md` with new architecture notes

---

## File Changes Summary

| File | Action |
|------|--------|
| `pipeline/openai_batch.py` | **CREATE** - OpenAI Batch API client |
| `pipeline/google_batch.py` | **CREATE** - Google batch embedding client |
| `pipeline/batch_ingestion.py` | **CREATE** - Pipeline coordinator |
| `pipeline/transcription.py` | **KEEP** - Encoding utilities |
| `pipeline/transcription_pipeline.py` | **DEPRECATE** - Old sync pipeline |
| `pipeline/embedding_pipeline.py` | **DEPRECATE** - Old sync pipeline |
| `core/settings.py` | **MODIFY** - Add batch settings |
| `backend/api.py` | **MODIFY** - New lifespan, status endpoint |
| `core/lancedb_client.py` | **MODIFY** - Batch insert method |
| `ui/src/components/ProcessingIndicator.tsx` | **CREATE** - Status display |
| `data/batch_state.json` | **RUNTIME** - State persistence |

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Transcription provider | OpenAI Batch API (GPT-4o) |
| Embedding provider | Google Gemini (gemini-embedding-exp-03-07) |
| Batch poll interval | 30 seconds |
| Failed file handling | Log error, don't retry. Next startup will detect via metadata |
| Batch size limits | Not a concern for expected data volume |
| Live updates | Not needed. Pipeline only runs on app startup |

---

## State File Format

`data/batch_state.json`:
```json
{
  "phase": "transcribing",
  "transcription_batch_id": "batch_abc123",
  "files_to_transcribe": ["2024-01-15.md", "2024-01-16.md"],
  "files_to_embed": [],
  "errors": [],
  "last_updated": "2024-01-18T10:30:00Z"
}
```

---

## Error Handling

- **Batch job fails**: Log batch ID and error, mark phase complete, continue to next phase
- **Individual file fails**: Log file path and error in state, skip file, continue processing others
- **App crashes mid-batch**: On restart, load state, poll existing batch job, resume from current phase
- **Batch expires** (24hr limit): Log warning, files will be picked up on next startup

---

## OpenAI Batch JSONL Format

```jsonl
{"custom_id": "2024-01-15-page-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-4o", "messages": [{"role": "user", "content": [{"type": "text", "text": "Transcribe this journal page..."}, {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}]}]}}
{"custom_id": "2024-01-15-page-2", "method": "POST", "url": "/v1/chat/completions", "body": {...}}
```
