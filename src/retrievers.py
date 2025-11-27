from completions import intent_classifier, get_embedding
from lancedb_client import LocalLanceDB
from models import ChatRequest, SearchOptions

class DocRetriever:
    def __init__(self, lance: LocalLanceDB):
        self.lance = lance

    def retrieve_docs(self, req: ChatRequest) -> dict:
        output_entries = []
        entries_str = ""
        
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
            print("query intent:", query_intent)

            if query_intent == SearchOptions.VECTOR:
                query_embedding = get_embedding(req.query)
                entries = self.lance.get_similar_entries(query_embedding, req.top_k)
                for i, (entry, distance) in enumerate(entries, 1):
                    entry_dict = entry.model_dump(exclude={"embedding"})
                    entries_str += f"Entry {i} (Distance: {distance})\n"
                    for k, v in entry_dict.items():
                        entries_str += f"   {k}: {v}\n"
                    entries_str += "\n"
                    output_entries.append((entry_dict, distance))

            elif query_intent == SearchOptions.RECENT:
                entries = self.lance.get_recent_entries()
                for i, entry in enumerate(entries, 1):
                    entry_dict = entry.model_dump(exclude={"embedding"})
                    entries_str += f"Entry {i}:\n"
                    for k, v in entry_dict.items():
                        entries_str += f"   {k}: {v}\n"
                    entries_str += "\n"
                    output_entries.append((entry_dict, "n/a"))
        
        return {
            "entries": output_entries,
            "entries_str": entries_str
        }
