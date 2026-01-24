from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.flows import default_llm_flow, agentic_llm_flow
from core.lancedb_client import AsyncLocalLanceDB
from core.models import (
    ChatRequest, ChatResponse,
    CreateThreadRequest, CreateThreadResponse, Thread,
    Message, AddMessageRequest, UpdateThreadRequest,
    StatusResponse
)

app_status = {"status": "starting"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("initializing database")
    db = AsyncLocalLanceDB("lance.journal-app")
    await db.connect()
    await db.startup_ingest()
    app.state.db = db
    app_status["status"] = "ready"

    yield

    print("shutting down")

app = FastAPI(lifespan=lifespan)


async def get_db() -> AsyncLocalLanceDB:
    """Dependency injection for database access."""
    return app.state.db

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

### status endpoint

@app.get("/status")
async def get_status() -> StatusResponse:
    return StatusResponse(status=app_status["status"])

### completion endpoints

@app.post("/journal_chat")
async def journal_chat(
    request: ChatRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> ChatResponse:
    return await default_llm_flow(db, request)


@app.post("/journal_chat_agent")
async def journal_chat_agent(
    request: ChatRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> ChatResponse:
    """Agentic chat endpoint that iteratively searches for relevant context."""
    return await agentic_llm_flow(db, request)

### thread management

@app.post("/threads")
async def create_new_thread(
    req: CreateThreadRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> CreateThreadResponse:
    """Create a new chat thread"""
    thread_doc = await db.create_thread(req.title, req.initial_message)
    return CreateThreadResponse(
        thread_id=thread_doc["thread_id"],
        created_at=thread_doc["created_at"]
    )


@app.get("/threads")
async def list_threads(db: AsyncLocalLanceDB = Depends(get_db)) -> list[Thread]:
    """Get all threads"""
    threads = await db.get_threads()
    return [Thread(**thread) for thread in threads]


@app.get("/threads/{thread_id}")
async def get_thread_details(
    thread_id: str,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> Thread:
    """Get a specific thread"""
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return Thread(**thread)


@app.get("/threads/{thread_id}/messages")
async def get_thread_messages_endpoint(
    thread_id: str,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> list[Message]:
    """Get all messages for a thread"""
    messages = await db.get_thread_messages(thread_id)
    return [Message(**msg) for msg in messages]


@app.post("/threads/{thread_id}/messages")
async def add_message_to_thread(
    thread_id: str,
    req: AddMessageRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> Message:
    """Add a message to a thread"""
    if not await db.get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")

    message_doc = await db.save_message(thread_id, req.role, req.content)
    return Message(**message_doc)


@app.put("/threads/{thread_id}")
async def update_thread_title(
    thread_id: str,
    req: UpdateThreadRequest,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> dict:
    """Update thread title"""
    if not await db.get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")

    await db.update_thread(thread_id, {"title": req.title})
    return {"message": "Thread title updated successfully"}


@app.delete("/threads/{thread_id}")
async def delete_thread_endpoint(
    thread_id: str,
    db: AsyncLocalLanceDB = Depends(get_db)
) -> dict:
    """Delete a thread"""
    success = await db.delete_thread(thread_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Thread deleted successfully"}
