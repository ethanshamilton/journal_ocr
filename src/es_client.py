# client code for interacting with Elasticsearch
import logging
import uuid
from datetime import datetime
from typing import Optional

from elasticsearch import Elasticsearch

from models import ChatRequest, Retrievers
from completions import get_embedding, intent_classifier

logging.basicConfig(filename="x.log")

### Elasticsearch Setup

es = Elasticsearch("http://localhost:9200")

if es.ping():
    logging.info("Elasticsearch is up")
else:
    logging.info("Could not connect.")

def create_chat_indexes() -> None:
    threads_mapping = {
        "mappings": {
            "properties": {
                "thread_id": {"type": "keyword"},
                "title": {"type": "text"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        }
    }

    messages_mapping = {
        "mappings": {
            "properties": {
                "thread_id": {"type": "keyword"},
                "message_id": {"type": "keyword"}, 
                "timestamp": {"type": "date"},
                "role": {"type": "keyword"},
                "content": {"type": "text"}
            }
        }
    }

    if not es.indices.exists(index="threads"):
        es.indices.create(index="threads", body=threads_mapping)
        logging.info("Created threads index")
    
    if not es.indices.exists(index="messages"):
        es.indices.create(index="messages", body=messages_mapping)
        logging.info("Created messages index")

### Search and Retrieval

def get_recent_entries(n: int = 7) -> list[dict]:
    """ Get the N most recent journals from elasticsearch. """
    response = es.search(
        index="journals",
        size=n,
        sort=[{"date": {"order": "desc"}}],
        query={"match_all": {}}
    )

    return [(hit["_source"], hit["_score"]) for hit in response["hits"]["hits"]]

def get_similar_entries(embedding: list[float], n: int) -> list[dict]:
    """ Run vector search on the elasticsearch index.  """
    response = es.search(
        index="journals",
        body={
            "size": n,
            "query": {
                "knn": {
                    "field": "embedding",
                    "query_vector": embedding,
                    "num_candidates": n
                }
            }
        }
    )

    return [(hit["_source"], hit["_score"]) for hit in response["hits"]["hits"]]

def get_entries_by_date_range(start_date: str, end_date: str, n: int = 100) -> list[dict]:
    """ Get journal entries between start_date and end_date (inclusive). """
    response = es.search(
        index="journals",
        size=n,
        sort=[{"date": {"order": "desc"}}],
        query={
            "range": {
                "date": {
                    "gte": start_date,
                    "lte": end_date
                }
            }
        }
    )

    return [(hit["_source"], hit["_score"]) for hit in response["hits"]["hits"]]

def retrieve_docs(req: ChatRequest) -> dict:
    """Retrieve relevant documents based on query intent"""
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

        if query_intent == Retrievers.VECTOR:
            query_embedding = get_embedding(req.query)
            entries = get_similar_entries(query_embedding, req.top_k)
        elif query_intent == Retrievers.RECENT:
            entries = get_recent_entries()

        # process entries
        for entry, _ in entries:
            if "embedding" in entry:
                del entry['embedding']
        
        for i, (entry, score) in enumerate(entries, 1):
            entries_str += f"Entry {i} (Score: {score}):\n"
            for k, v in entry.items():
                entries_str += f"  {k}: {v}\n"
            entries_str += "\n"
    
    return {
        "entries": entries,
        "entries_str": entries_str
    }

### Thread Management

def create_thread(title: Optional[str] = None, initial_message: Optional[str] = None) -> dict:
    """Create a new thread in elasticsearch"""
    thread_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    thread_doc = {
        "thread_id": thread_id,
        "title": title or f"Chat {now.strftime('%Y-%m-%d %H:%M')}",
        "tags": [],
        "created_at": now,
        "updated_at": now
    }
    
    es.index(index="threads", id=thread_id, body=thread_doc)
    
    # if initial message provided, save it
    if initial_message:
        save_message(thread_id, "user", initial_message)
    
    return thread_doc

def get_threads() -> list[dict]:
    """Get all threads sorted by updated_at desc"""
    response = es.search(
        index="threads",
        size=100,
        sort=[{"updated_at": {"order": "desc"}}],
        query={"match_all": {}}
    )
    
    return [hit["_source"] for hit in response["hits"]["hits"]]

def get_thread(thread_id: str) -> Optional[dict]:
    """Get a specific thread by id"""
    try:
        response = es.get(index="threads", id=thread_id)
        return response["_source"]
    except Exception:
        return None

def get_thread_messages(thread_id: str) -> list[dict]:
    """Get all messages for a thread"""
    response = es.search(
        index="messages",
        size=1000,
        sort=[{"timestamp": {"order": "asc"}}],
        query={"term": {"thread_id": thread_id}}
    )
    
    return [hit["_source"] for hit in response["hits"]["hits"]]

def save_message(thread_id: str, role: str, content: str) -> dict:
    """Save a message to a thread"""
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    message_doc = {
        "message_id": message_id,
        "thread_id": thread_id,
        "timestamp": now,
        "role": role,
        "content": content
    }
    
    es.index(index="messages", id=message_id, body=message_doc)
    
    # update thread's updated_at timestamp
    es.update(
        index="threads",
        id=thread_id,
        body={"doc": {"updated_at": now}}
    )
    
    return message_doc

def delete_thread(thread_id: str) -> bool:
    """Delete a thread and all its messages"""
    try:
        # delete all messages for this thread
        es.delete_by_query(
            index="messages",
            body={"query": {"term": {"thread_id": thread_id}}}
        )
        
        # delete the thread
        es.delete(index="threads", id=thread_id)
        
        return True
    except Exception:
        return False
