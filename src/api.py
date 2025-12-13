from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from flows import comprehensive_analysis_flow, default_llm_flow
from lancedb_client import AsyncLocalLanceDB
from models import (
    ChatRequest, ChatResponse, 
    CreateThreadRequest, CreateThreadResponse, Thread, 
    Message, AddMessageRequest, UpdateThreadRequest
)

lance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("initializing database")
    global lance
    lance = AsyncLocalLanceDB("lance.journal-app")
    await lance.connect()
    await lance.startup_ingest()
    app.state.db = lance

    yield

    print("shutting down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

### completion endpoints

@app.post("/journal_chat")
async def journal_chat(request: ChatRequest) -> ChatResponse:
    global lance
    return default_llm_flow(lance, request)

@app.post("/comprehensive_analysis")
async def comprehensive_journal_analysis(request: ChatRequest) -> dict:
    global lance
    return comprehensive_analysis_flow(lance, request)

### thread management

@app.post("/threads")
async def create_new_thread(req: CreateThreadRequest) -> CreateThreadResponse:
    """Create a new chat thread"""
    global lance
    thread_doc = await lance.create_thread(req.title, req.initial_message)
    return CreateThreadResponse(
        thread_id=thread_doc["thread_id"],
        created_at=thread_doc["created_at"]
    )

@app.get("/threads")
async def list_threads() -> list[Thread]:
    """Get all threads"""
    global lance
    threads = await lance.get_threads()
    return [Thread(**thread) for thread in threads]

@app.get("/threads/{thread_id}")
async def get_thread_details(thread_id: str) -> Thread:
    """Get a specific thread"""
    global lance
    thread = await lance.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return Thread(**thread)

@app.get("/threads/{thread_id}/messages")
async def get_thread_messages_endpoint(thread_id: str) -> list[Message]:
    """Get all messages for a thread"""
    global lance
    messages = await lance.get_thread_messages(thread_id)
    return [Message(**msg) for msg in messages]

@app.post("/threads/{thread_id}/messages")
async def add_message_to_thread(thread_id: str, req: AddMessageRequest) -> Message:
    """Add a message to a thread"""
    global lance
    if not await lance.get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")

    message_doc = await lance.save_message(thread_id, req.role, req.content)
    return Message(**message_doc)

@app.put("/threads/{thread_id}")
async def update_thread_title(thread_id: str, req: UpdateThreadRequest) -> dict:
    """Update thread title"""
    global lance
    if not await lance.get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")

    await lance.update_thread(thread_id, {"title": req.title})
    return {"message": "Thread title updated successfully"}

@app.delete("/threads/{thread_id}")
async def delete_thread_endpoint(thread_id: str) -> dict:
    """Delete a thread"""
    global lance
    success = await lance.delete_thread(thread_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Thread deleted successfully"}
