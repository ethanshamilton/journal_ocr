from contextlib import asynccontextmanager
from datetime import datetime
import json
import hashlib
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from es_client import (
    create_thread, retrieve_docs, get_entries_by_date_range,
    get_threads, get_thread, get_thread_messages,
    save_message, delete_thread, es
)
from completions import chat_response, comprehensive_analysis
from lancedb_client import LocalLanceDB
from models import (
    ChatRequest, ChatResponse, 
    CreateThreadRequest, CreateThreadResponse, Thread, 
    Message, AddMessageRequest, UpdateThreadRequest
)
from retrievers import DocRetriever

lance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("initializing database")
    global lance
    lance = LocalLanceDB("lance.journal-app")
    lance.startup_ingest()
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
    doc_retriever = DocRetriever(lance)
    retrieval_result = doc_retriever.retrieve_docs(request)
    entries = retrieval_result["entries"]
    entries_str = retrieval_result["entries_str"]

    # prepare chat history
    chat_history = load_chat_history(request)

    # generate response
    print("attempting llm response")
    llm_response = chat_response(request, chat_history, entries_str)
    print(llm_response)

    return ChatResponse(response=llm_response, docs=entries, thread_id=request.thread_id)

@app.post("/comprehensive_analysis")
async def comprehensive_journal_analysis(request: ChatRequest) -> dict:
    # create cache key based on query and model
    cache_key = hashlib.md5(f"{request.query}_{request.provider}_{request.model}".encode()).hexdigest()
    cache_file = f"data/comprehensive_analysis_{cache_key}.json"
    
    # check if cached result exists
    if os.path.exists(cache_file):
        print(f"loading cached analysis from {cache_file}")
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
            return cached_data
    
    print(f"running comprehensive analysis (will cache to {cache_file})")
    
    # prepare chat history
    chat_history = load_chat_history(request)

    # iterate through years from 2018 to present
    current_year = datetime.now().year
    years = list(range(2018, current_year + 1))

    analyses = []
    for year in years:
        print(f"\nprocessing year: {year}")
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        entries = get_entries_by_date_range(start_date, end_date)
        
        # process entries (remove embeddings)
        for entry, _ in entries:
            if "embedding" in entry:
                del entry['embedding']
        
        # format entries_str like in retrieve_docs
        entries_str = ""
        for i, (entry, score) in enumerate(entries, 1):
            entries_str += f"Entry {i} (Score: {score}):\n"
            for k, v in entry.items():
                entries_str += f"  {k}: {v}\n"
            entries_str += "\n"

        # create fresh chat history for each year to avoid contamination
        year_chat_history = load_chat_history(request)
        
        # run year analysis
        analysis = comprehensive_analysis(request, year_chat_history, entries_str, "YEAR")
        analyses.append(analysis)
        print(f"\nreasoning: {analysis.reasoning}\n\nanalysis: {analysis.analysis}\n\nexcerpts: {analysis.excerpts}\n")

    analyses_str = ""
    for analysis in analyses:
        analyses_str += f"""
        <ANALYSIS>{analysis.analysis}</ANALYSIS>
        <EXCERPTS>{analysis.excerpts}</EXCERPTS>
        """
    final_analysis = comprehensive_analysis(request, chat_history, analyses_str, "FINAL")
    print(f"\nFINAL ANALYSIS\n\nreasoning: {final_analysis.reasoning}\n\nanalysis: {final_analysis.analysis}\n\nexcerpts: {final_analysis.excerpts}\n")

    # prepare result for caching
    result = {
        "query": request.query,
        "provider": request.provider,
        "model": request.model,
        "timestamp": datetime.now().isoformat(),
        "year_analyses": [
            {
                "year": year,
                "reasoning": analysis.reasoning,
                "analysis": analysis.analysis,
                "excerpts": analysis.excerpts
            }
            for year, analysis in zip(years, analyses)
        ],
        "final_analysis": {
            "reasoning": final_analysis.reasoning,
            "analysis": final_analysis.analysis,
            "excerpts": final_analysis.excerpts
        }
    }
    
    # save to cache
    os.makedirs("data", exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"analysis cached to {cache_file}")
    return result

### thread management

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

### utilities

def load_chat_history(request: ChatRequest) -> list[dict]:
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

    return es_messages + temp_messages
