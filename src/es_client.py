# client code for interacting with Elasticsearch
import logging

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
