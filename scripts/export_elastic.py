import json
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from elasticsearch.helpers import scan
from src.es_client import es

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
EXPORT_FILE = os.path.join(DATA_DIR, 'chat_history_export.json')

def export_from_es():
    print("Starting export from Elasticsearch...")
    
    # Export Threads
    print("Exporting threads...")
    threads = []
    # Use scan to get all documents
    es_threads = scan(es, index="threads", query={"query": {"match_all": {}}})
    
    for hit in es_threads:
        source = hit['_source']
        # Ensure tags is a list
        if source.get('tags') is None:
            source['tags'] = []
        threads.append(source)
    
    print(f"Found {len(threads)} threads.")

    # Export Messages
    print("Exporting messages...")
    messages = []
    es_messages = scan(es, index="messages", query={"query": {"match_all": {}}})
    
    for hit in es_messages:
        messages.append(hit['_source'])
        
    print(f"Found {len(messages)} messages.")
    
    export_data = {
        "threads": threads,
        "messages": messages
    }
    
    with open(EXPORT_FILE, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
        
    print(f"Exported data to {EXPORT_FILE}")
    return export_data

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    export_from_es()
