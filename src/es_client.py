# client code for interacting with Elasticsearch
import logging

from elasticsearch import Elasticsearch

logging.basicConfig(filename="x.log")

es = Elasticsearch("http://localhost:9200")

if es.ping():
    logging.info("Elasticsearch is up")
else:
    logging.info("Could not connect.")

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
