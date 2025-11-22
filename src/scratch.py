from completions import get_embedding
from lancedb_client import LocalLanceDB

lance = LocalLanceDB("lancedb-experiment")
lance.startup_ingest()

recent_entries = lance.get_recent_entries()
print(recent_entries.shape)

query = "i have to go to australia soon for work. it's going to be a good trip working for future fund but kind of stressful."

query_embed = get_embedding(query)

results = lance.get_similar_entries(query_embed)
print(results)
