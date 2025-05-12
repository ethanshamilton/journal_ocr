# client code for interacting with Elasticsearch
import logging

from elasticsearch import Elasticsearch

logging.basicConfig(filename="x.log")

es = Elasticsearch("http://localhost:9200")

if es.ping():
    logging.info("Elasticsearch is up")
else:
    logging.info("Could not connect.")

def get_recent_journals(n: int = 10) -> dict:
    """ Get the N most recent journals from elasticsearch. """
    response = es.search(
        index="journals",
        size=n,
        sort=[{"date": {"order": "desc"}}],
        query={"match_all": {}}
    )

    response = [hit["_source"] for hit in response["hits"]["hits"]]

    return response
