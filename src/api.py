from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from es_client import (
    get_similar_entries, create_thread, retrieve_docs,
    get_threads, get_thread, get_thread_messages,
    save_message, delete_thread, es
)
from completions import get_embedding, query_llm, chat_response
from models import (
    QueryRequest, LLMRequest, ChatRequest, ChatResponse, 
    CreateThreadRequest, CreateThreadResponse, Thread, 
    Message, AddMessageRequest, UpdateThreadRequest
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/similar_entries")
def similar_entries(req: QueryRequest) -> dict:
    """ Returns K-nearest neighbors of query.  """
    embedding = get_embedding(req.query)
    results = get_similar_entries(embedding, req.top_k)
    for entry, _ in results:
        if "embedding" in entry:
            del entry['embedding']
    return { "results": results }

@app.post("/query_llm")
def _query_llm(req: LLMRequest) -> dict:
    """ General LLM query endpoint. """
    response = query_llm(req.prompt, req.provider, req.model)
    return { "response": response.content[0].text }

@app.post("/journal_chat")
async def journal_chat(request: ChatRequest) -> ChatResponse:
    # retrieve documents using the new endpoint logic
    retrieval_result = retrieve_docs(request)
    entries = retrieval_result["entries"]
    entries_str = retrieval_result["entries_str"]

    # get thread history from elasticsearch if present
    es_messages = []
    if request.thread_id:
        try:
            thread_messages = get_thread_messages(request.thread_id)
            if thread_messages:
                for msg in thread_messages:
                    role = msg.get("role", "user")
                    if role not in ["user", "assistant"]:
                        role = "user"
                    content = msg.get("content", "")
                    es_messages.append({"role": role, "content": content})
        except Exception as e:
            print(f"Error loading thread messages: {e}")

    # also include message history from request if provided (for temporary chats)
    temp_messages = []
    if request.message_history:
        for msg in request.message_history:
            role = msg.get("sender", "user")
            if role not in ["user", "assistant"]:
                role = "user"
            content = msg.get("text", "")
            temp_messages.append({"role": role, "content": content})

    chat_history = es_messages + temp_messages

    # generate response
    llm_response = chat_response(request, chat_history, entries_str)

    return ChatResponse(response=llm_response, docs=entries, thread_id=request.thread_id)

# Thread management endpoints
@app.post("/threads")
def create_new_thread(req: CreateThreadRequest) -> CreateThreadResponse:
    """Create a new chat thread"""
    thread_doc = create_thread(req.title, req.initial_message)
    return CreateThreadResponse(
        thread_id=thread_doc["thread_id"],
        created_at=thread_doc["created_at"]
    )

@app.get("/threads")
def list_threads() -> list[Thread]:
    """Get all threads"""
    threads = get_threads()
    return [Thread(**thread) for thread in threads]

@app.get("/threads/{thread_id}")
def get_thread_details(thread_id: str) -> Thread:
    """Get a specific thread"""
    thread = get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return Thread(**thread)

@app.get("/threads/{thread_id}/messages")
def get_thread_messages_endpoint(thread_id: str) -> list[Message]:
    """Get all messages for a thread"""
    messages = get_thread_messages(thread_id)
    return [Message(**msg) for msg in messages]

@app.post("/threads/{thread_id}/messages")
def add_message_to_thread(thread_id: str, req: AddMessageRequest) -> Message:
    """Add a message to a thread"""
    # verify thread exists
    if not get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    
    message_doc = save_message(thread_id, req.role, req.content)
    return Message(**message_doc)

@app.put("/threads/{thread_id}")
def update_thread_title(thread_id: str, req: UpdateThreadRequest) -> dict:
    """Update thread title"""
    # verify thread exists
    if not get_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # update thread title in elasticsearch
    es.update(
        index="threads",
        id=thread_id,
        body={"doc": {"title": req.title}}
    )
    return {"message": "Thread title updated successfully"}

@app.delete("/threads/{thread_id}")
def delete_thread_endpoint(thread_id: str) -> dict:
    """Delete a thread"""
    success = delete_thread(thread_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"message": "Thread deleted successfully"}
