from completions import get_embedding, query_llm
from es_client import get_similar_entries

query = "What kind of goals are consistently important to me? What things give me purpose and fulfillment?"

query_embedding = get_embedding(query)
similar_entries = get_similar_entries(query_embedding, 7)

entries_str = ""
for i, (entry, score) in enumerate(similar_entries, 1):
    entries_str += f"Entry {i} (Score: {score}):\n"
    for k, v in entry.items():
        if k == "embedding":
            continue
        entries_str += f"  {k}: {v}\n"
    entries_str += "\n"

prompt = f"""
    I am giving you access to some of my journal entries in order to help answer the following question:
    {query}

    Here are the journal entries:
    {entries_str}
"""

llm_response = query_llm(prompt, "anthropic", "claude-3-5-sonnet-20240620")

print(entries_str)
print("")
print(" --- ")
print("")
print(llm_response.content[0].text)
