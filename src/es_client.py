# client code for interacting with Elasticsearch
import logging
import uuid
from datetime import datetime
from typing import Optional

from elasticsearch import Elasticsearch

logging.basicConfig(filename="x.log")

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

def get_recent_entries(n: int = 7) -> list[dict]:
    """ Get the N most recent journals from elasticsearch. """
    response = es.search(
        index="journals",
        size=n,
        sort=[{"date": {"order": "desc"}}],
        query={"match_all": {}}
    )

    return [(hit["_source"], hit["_score"]) for hit in response["hits"]["hits"]]

def get_similar_entries(embedding: list[float], n: int) -> dict:
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

# Thread management functions
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
