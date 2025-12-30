# Integrated App Startup

## Startup Flow

1. Launch frontend with loading screen
2. Launch pipeline to crawl the source folder and process any new docs
3. After the pipeline is finished running, start the backend
4. Once the backend is active, change frontend to main screen
   - Frontend pings backend every 2s for status update

---

## Implementation Plan

### Files to Modify/Create

| File | Action |
|------|--------|
| `launch_app.sh` | CREATE - Shell script orchestrator |
| `backend/src/backend/api.py` | MODIFY - Add `/status` endpoint |
| `backend/src/core/models.py` | MODIFY - Add StatusResponse model |
| `ui/src/services/api.ts` | MODIFY - Add checkStatus method |
| `ui/src/components/LoadingScreen.tsx` | CREATE - Loading screen component |
| `ui/src/components/LoadingScreen.css` | CREATE - Loading screen styles |
| `ui/src/App.tsx` | MODIFY - Add polling and conditional rendering |

---

### Step 1: Backend Status Endpoint

**File:** `backend/src/core/models.py`
- Add `StatusResponse` Pydantic model with `status: str` field

**File:** `backend/src/backend/api.py`
- Add module-level `app_status = {"status": "starting"}`
- Update lifespan to set `app_status["status"] = "ready"` after initialization
- Add `GET /status` endpoint that returns `StatusResponse`

---

### Step 2: Frontend API Service

**File:** `ui/src/services/api.ts`
- Add `StatusResponse` interface
- Add `checkStatus()` method to `apiService`:
```typescript
async checkStatus(): Promise<StatusResponse> {
  const response = await api.get<StatusResponse>('/status')
  return response.data
}
```

---

### Step 3: Loading Screen Component

**File:** `ui/src/components/LoadingScreen.tsx`
- Horizontal Matrix rain effect (characters flowing left → right)
- Use canvas element for smooth animation
- Random characters: mix of katakana, numbers, journal-related symbols
- Multiple streams at different speeds/opacities
- "Loading Journal" text centered over the effect
- Match existing dark theme (#181a20 background, #ff8800 orange streams)

**File:** `ui/src/components/LoadingScreen.css`
- Full viewport canvas as background
- Centered overlay text with slight transparency
- Canvas positioned absolute behind content

---

### Step 4: App.tsx Polling Logic

**File:** `ui/src/App.tsx`
- Add `isBackendReady` state (default: false)
- Add `useEffect` hook that:
  - Calls `apiService.checkStatus()` on mount
  - Polls every 2 seconds until status is "ready"
  - Sets `isBackendReady = true` when ready
  - Catches errors silently (backend not up yet)
- Conditionally render `<LoadingScreen />` or main app

---

### Step 5: Shell Script Orchestrator

**File:** `launch_app.sh` (project root)

```bash
#!/bin/bash
# 1. Start frontend (npm run dev) in background
# 2. Run pipeline (uv run python -m pipeline.ingestion_pipeline) - blocking
# 3. Start backend (uv run uvicorn backend.api:app) in background
# 4. Trap SIGINT/SIGTERM for graceful shutdown
```

Key points:
- Store PIDs for cleanup
- Use `trap` for Ctrl+C handling
- Kill both frontend and backend on exit

---

## Implementation Order

1. Backend changes (can test independently with `curl /status`)
2. Frontend API service addition
3. LoadingScreen component
4. App.tsx modifications
5. Shell script (ties everything together)

---

## Testing

1. **Backend:** Start manually, verify `curl http://localhost:8000/status` returns `{"status":"ready"}`
2. **Frontend:** Start without backend, verify loading screen shows; start backend, verify transition
3. **E2E:** Run `./launch_app.sh`, observe full flow, test Ctrl+C shutdown

---

## Future Enhancements

- Frontend could receive info about pipeline processing (file counts, progress)
- Add retry mechanism for pipeline failures
- Add port availability checks in launch script
