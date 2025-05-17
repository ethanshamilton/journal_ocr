from completions import get_embedding
from es_client import get_similar_entries

query = "Music, considering whether it is worth pursuing or not for the main goal of my life"

query_embedding = get_embedding(query)
similar_entries = get_similar_entries(query_embedding, 10)

for entry in similar_entries:
    print(entry[0]['title'])
    print(entry[0]['text'])
    print("")
    print("---")
    print("")
