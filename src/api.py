from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from baml_client.types import Retrievers
from es_client import get_similar_entries, get_recent_entries
from completions import get_embedding, query_llm, intent_classifier
from models import QueryRequest, LLMRequest, ChatRequest, ChatResponse

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
def query_journal(req: ChatRequest) -> ChatResponse:
    # determine which retriever to use
    query_intent = intent_classifier(req.query)

    if query_intent == Retrievers.Vector:
        query_embedding = get_embedding(req.query)
        entries = get_similar_entries(query_embedding, req.top_k)
    elif query_intent == Retrievers.Recent:
        entries = get_recent_entries()

    # process entries
    for entry, _ in entries:
        if "embedding" in entry:
            del entry['embedding']
    
    entries_str = ""
    for i, (entry, score) in enumerate(entries, 1):
        entries_str += f"Entry {i} (Score: {score}):\n"
        for k, v in entry.items():
            entries_str += f"  {k}: {v}\n"
        entries_str += "\n"

    # response generation
    prompt = f"""
    I am giving you access to some of my journal entries in order to help answer the following question:
    {req.query}

    Here are the journal entries:
    {entries_str}
    """

    llm_response = query_llm(prompt, req.provider, req.model)
    return ChatResponse(response=llm_response, docs=entries)
