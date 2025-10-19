from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json

from baml_client.types import Retrievers
from es_client import get_similar_entries, get_recent_entries, create_thread, get_threads, get_thread, get_thread_messages, save_message, delete_thread, es
from completions import get_embedding, query_llm, intent_classifier
from models import QueryRequest, LLMRequest, ChatRequest, ChatResponse, CreateThreadRequest, CreateThreadResponse, Thread, Message, AddMessageRequest, UpdateThreadRequest

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

@app.post("/query_journal")
async def query_journal(request: Request) -> ChatResponse:
    # get raw body first
    body = await request.body()
    print(f"Raw body: {body}")
    print(f"Raw body as string: {body.decode()}")
    
    # try to parse as json
    try:
        json_data = json.loads(body)
        print(f"Parsed JSON: {json_data}")
    except Exception as e:
        print(f"JSON parse error: {e}")
    
    # now try to create the pydantic model
    try:
        req = ChatRequest(**json_data)
        print(f"Pydantic model created successfully: {req}")
    except Exception as e:
        print(f"Pydantic model error: {e}")
        raise
    # determine which retriever to use
    entries = []
    entries_str = ""
    
    # if we have existing docs, use those instead of doing retrieval
    if req.existing_docs:
        entries_str = "Here are the relevant journal entries from our previous conversation:\n"
        for i, doc in enumerate(req.existing_docs, 1):
            entries_str += f"Entry {i}:\n"
            entries_str += f"  title: {doc.get('title', 'Untitled')}\n"
            entries_str += f"  content: {doc.get('content', '')}\n"
            entries_str += "\n"
    else:
        # do normal retrieval
        query_intent = intent_classifier(req.query)

        if query_intent == Retrievers.Vector:
            query_embedding = get_embedding(req.query)
            entries = get_similar_entries(query_embedding, req.top_k)
        elif query_intent == Retrievers.Recent:
            entries = get_recent_entries()
        elif query_intent == Retrievers.NoRetriever:
            pass

        # process entries
        for entry, _ in entries:
            if "embedding" in entry:
                del entry['embedding']
        
        for i, (entry, score) in enumerate(entries, 1):
            entries_str += f"Entry {i} (Score: {score}):\n"
            for k, v in entry.items():
                entries_str += f"  {k}: {v}\n"
            entries_str += "\n"

    # get thread message history if thread_id provided
    thread_history = ""
    if req.thread_id:
        try:
            thread_messages = get_thread_messages(req.thread_id)
            if thread_messages:
                thread_history = "\n\nPrevious conversation:\n"
                for msg in thread_messages:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    thread_history += f"{role}: {msg['content']}\n"
        except Exception as e:
            print(f"Error loading thread messages: {e}")

    # also include message history from request if provided (for temporary chats)
    temp_history = ""
    if req.message_history:
        temp_history = "\n\nCurrent conversation:\n"
        for msg in req.message_history:
            role = "User" if msg.get("sender") == "user" else "Assistant"
            content = msg.get("text", "")
            temp_history += f"{role}: {content}\n"

    # response generation
    prompt = f"""
    I am giving you access to some of my journal entries in order to help answer the following question:
    {req.query}

    Here are the journal entries:
    {entries_str}{thread_history}{temp_history}
    """

    llm_response = query_llm(prompt, req.provider, req.model)
    return ChatResponse(response=llm_response, docs=entries, thread_id=req.thread_id)

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
