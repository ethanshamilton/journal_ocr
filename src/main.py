from completions import get_embedding
from es_client import get_similar_entries

query = "Philosophy, metaphysics, existentialism. Why am I here, what is my purpose?"

query_embedding = get_embedding(query)
similar_entries = get_similar_entries(query_embedding, 10)

for entry in similar_entries:
    print(entry)
    print("")
