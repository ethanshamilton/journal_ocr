# Journal OCR EC2 Deployment and OneDrive Access Plan

## Goal
Deploy `journal_ocr` so it is securely reachable only by you from anywhere, while replacing the current workstation-local journal data assumptions with a reliable OneDrive-backed synchronization model.

## Recommended end state
- Single EC2 instance with EBS-backed persistent storage.
- Nginx serves the built frontend and reverse-proxies the FastAPI backend.
- FastAPI binds to localhost only; it is never directly internet-exposed.
- Access is private-only over Tailscale.
- Journal content remains in OneDrive as the upstream source of truth.
- EC2 maintains a local cache, metadata store, and LanceDB index for fast retrieval.
- Sync/index work is separated from API startup.

## Key decisions
### 1. Access model
Use a private network overlay, not a public app.
- Install Tailscale on EC2 and on your personal devices.
- Do not expose the application publicly on ports 80/443 unless a later requirement forces it.
- Keep SSH private as well: prefer Tailscale SSH or key-only SSH restricted to your IP.

Why:
- The app contains highly sensitive journal data.
- You are the only intended user.
- Private-network access removes the largest attack surface without forcing a browser auth stack into the first deployment.

### 2. Deployment model
Use a single-instance deployment first.
- EC2 hosts frontend, backend, local cache, metadata store, and LanceDB.
- systemd manages long-running services.
- Nginx handles static frontend hosting and local reverse proxying.

Why:
- The current codebase is a single-host local-data system.
- Splitting services before separating startup ingestion from serving would increase complexity without improving reliability.

### 3. Data access model
Do not query OneDrive directly on each user request.
- Use Microsoft Graph to discover and download changes.
- Maintain a local cache of changed markdown, PDF, and image files on EC2.
- Build and serve search from local LanceDB.

Why:
- Current retrieval is index-based, not direct-document-based.
- OCR, embeddings, and search need local working data.
- Direct per-request Graph calls would move latency, throttling, and auth fragility into the hot path.

## Current codebase constraints that must be addressed
1. `ui/src/services/api.ts` hardcodes `http://localhost:8000`.
2. `backend/src/backend/api.py` hardcodes localhost-only CORS origins.
3. `backend/src/core/settings.py` hardcodes machine-specific absolute paths.
4. `backend/src/backend/api.py` starts `AsyncLocalLanceDB("lance.journal-app")` with a relative path.
5. `backend/src/backend/api.py` always calls `startup_ingest()` during app startup.
6. `backend/src/core/lancedb_client.py` rebuilds the journal table from local files on startup.
7. `pipeline` code currently stores processing state by mutating markdown frontmatter and writing local embeddings JSONL.

These assumptions are acceptable for local development but not for a reliable hosted deployment.

## Phase plan

### Phase 1: Make the app deployable on a single host
Objective: remove local-development assumptions so the app can run predictably on EC2.

Work:
1. Replace hardcoded frontend API URL with environment-driven or same-origin relative API paths.
2. Replace hardcoded backend allowed origins with environment-driven config, or simplify to same-origin deployment.
3. Replace absolute local file paths with deploy-time configuration for:
   - journal cache root
   - evergreen cache root
   - chats storage path
   - embeddings/state path
   - LanceDB path
4. Move LanceDB path to an explicit persistent directory on EBS.
5. Remove `--reload` and any dev-only process assumptions from production start commands.
6. Separate “open existing DB” from “sync/index/rebuild data”.

Acceptance criteria:
- The backend can start on EC2 without any `/Users/...` paths.
- The frontend can talk to the backend without `localhost` assumptions.
- A backend restart does not require a full data rebuild to become ready.

### Phase 2: Build a secure private-only EC2 deployment
Objective: make the app reachable only by you.

Work:
1. Provision Ubuntu EC2 with encrypted EBS storage.
2. Install Python 3.13, `uv`, Node/npm, Nginx, and Tailscale.
3. Build the frontend once with `npm run build`.
4. Run FastAPI behind systemd, bound to `127.0.0.1:8000`.
5. Serve the built frontend with Nginx.
6. Install Tailscale and restrict access to the private tailnet.
7. Keep security groups minimal:
   - no public backend port
   - no public frontend port for the private-only design
   - no open SSH to the world
8. Store secrets outside the repo, ideally in an env file with restrictive permissions or AWS secret storage.
9. Run the app as a dedicated non-root Linux user.

Acceptance criteria:
- The app is reachable from your authorized devices over Tailscale.
- The app is not reachable from the public internet.
- The backend is only accessible via Nginx or localhost.
- Secrets are not stored in the repository.

### Phase 3: Introduce a OneDrive sync boundary
Objective: stop treating your local workstation folder layout as the source of truth.

Work:
1. Add a OneDrive/Graph integration layer responsible for:
   - drive/folder discovery
   - delta query polling
   - changed file download
   - deletion detection
2. Persist sync state locally, including:
   - drive ID
   - item ID
   - path
   - etag/ctag
   - last synced timestamp
   - delta token
3. Materialize changed files into a local EC2 cache directory.
4. Keep cache layout stable so indexing code has predictable file paths.
5. Use Graph delta as the main change feed.
6. Optionally use webhooks as a trigger, but still resolve actual changes via delta.

Acceptance criteria:
- The sync service can detect and download only changed files.
- Full-vault download is not required on every startup.
- Local cache becomes the input to indexing and OCR.

### Phase 4: Move processing state out of journal markdown
Objective: stop using source markdown as application bookkeeping.

Work:
1. Replace frontmatter-tracked processing fields with app-owned metadata, including:
   - transcription status
   - embedding status
   - content hash
   - embedding version
   - last processed timestamp
2. Move embeddings bookkeeping out of local JSONL-as-truth and into an explicit app-managed state boundary.
3. Preserve markdown content as source content; do not use remote writes as a routine operational path.
4. Keep deliberate remote writes optional and explicit, not part of normal sync/index flow.

Acceptance criteria:
- The app no longer depends on writing frontmatter updates back to the OneDrive source files.
- Processing metadata can be updated independently of source document storage.

### Phase 5: Make indexing incremental
Objective: update only what changed instead of rebuilding the journal dataset each time.

Work:
1. Convert ingestion from full startup rebuild to explicit incremental jobs.
2. Re-run OCR only for newly changed image/PDF inputs.
3. Recompute embeddings only for changed markdown/transcription content.
4. Update LanceDB incrementally instead of overwriting the full journal table on each boot.
5. Add an explicit bootstrap/rebuild command for first-time indexing or disaster recovery.

Acceptance criteria:
- API startup opens existing state without blocking on a full ingest.
- Index maintenance can run independently of request serving.
- Changed journal content appears after sync/index without full-table rebuild.

## EC2 runtime layout
Recommended directory layout:
- `/srv/journal_ocr/app` — repo checkout
- `/srv/journal_ocr/cache/journal` — synced journal cache
- `/srv/journal_ocr/cache/evergreen` — synced evergreen cache
- `/srv/journal_ocr/state/lancedb` — LanceDB files
- `/srv/journal_ocr/state/metadata` — sync and processing metadata
- `/srv/journal_ocr/state/logs` — app logs
- `/etc/journal_ocr/backend.env` — backend secrets/config

## Service layout
Recommended long-running processes:
1. `journal-ocr-web`
   - Nginx serving frontend and proxying local API.
2. `journal-ocr-api`
   - FastAPI/Uvicorn service on localhost.
3. `journal-ocr-sync`
   - scheduled or daemonized OneDrive delta sync.
4. `journal-ocr-index`
   - incremental OCR/embedding/index worker, either scheduled or queue-triggered.

Initial simplification:
- `sync` and `index` can start as one sequential job if needed.
- Keep them separate in design even if implemented as one process initially.

## Security controls
### Network
- Prefer Tailscale-only access.
- No public backend exposure.
- Avoid public frontend exposure unless later required.
- Keep Uvicorn on localhost only.

### Host
- Dedicated non-root app user.
- SSH keys only if SSH remains enabled.
- Automatic security updates.
- Minimal installed services.

### Secrets
- Store API keys and Microsoft credentials outside the repo.
- Restrict file permissions tightly.
- Never log access tokens or sensitive journal content unnecessarily.

### Data protection
- Enable EBS encryption.
- Restrict access to cache, metadata, and LanceDB directories.
- Decide retention explicitly for raw downloads, transcripts, embeddings, and chat history.
- Back up only what is necessary; encrypt backups.

## OneDrive authentication recommendation
Preferred:
- If the journal is in OneDrive for Business / SharePoint, use app-only Microsoft Graph access.

Fallback:
- If the journal is in personal OneDrive, use delegated auth with refresh-token handling.

Implication:
- Personal OneDrive works, but unattended server operation is less clean than Business/SharePoint.
- If long-term unattended hosting matters, moving the data to a business/SharePoint-backed drive is operationally stronger.

## Delivery sequence
Recommended order of execution:
1. Make configuration environment-driven.
2. Remove startup ingestion from normal API boot.
3. Make frontend/backend same-origin deployable.
4. Deploy private-only EC2 instance with local persistent state.
5. Get the app working with a local synced journal copy on EC2.
6. Add Graph delta-based sync.
7. Move processing metadata out of markdown/frontmatter.
8. Convert indexing to incremental updates.
9. Add optional webhook triggers after delta polling works reliably.

## Risks and mitigations
### Risk: API restart becomes unavailable during sync/index
Mitigation:
- separate serving startup from sync/index work
- keep previous local index available until new updates finish

### Risk: remote file semantics cause corruption or slowdowns
Mitigation:
- do not treat OneDrive as a live filesystem in the hot path
- use local cache plus explicit sync metadata

### Risk: sensitive data exposure
Mitigation:
- private-only Tailscale access
- localhost-only backend
- encrypted storage
- minimal logs
- secrets outside repo

### Risk: auth/token fragility for personal OneDrive
Mitigation:
- start with delegated auth if required
- consider migration to OneDrive for Business/SharePoint if unattended reliability becomes important

## Definition of done
This plan is complete when:
- the app is privately reachable only by you over Tailscale
- EC2 no longer depends on your workstation filesystem layout
- OneDrive is integrated as an upstream sync source, not a per-request dependency
- journal indexing and API serving are decoupled
- processing metadata no longer depends on rewriting source markdown during normal operation

## Immediate next action
Start with Phase 1 and Phase 2 together: make the app deployable, then stand up a private-only EC2 deployment using local cached data before introducing Graph sync.