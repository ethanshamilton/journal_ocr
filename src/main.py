from baml_client import b
from baml_client.types import Retrievers
from completions import get_embedding, intent_classifier
from es_client import get_recent_entries

query = "Based on recent events, what should I focus on to improve this week?"

query_embedding = get_embedding(query)
intent_classification = intent_classifier(query)
# similar_entries = get_similar_entries(query_embedding, 7)
# recent_entries = get_recent_entries()

print(type(intent_classification))

if intent_classification == Retrievers.Date:
    print("Date")
