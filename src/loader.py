# loader.py
# loads data into elasticsearch
import os
import re
import json
import glob
import time
import logging
import requests
from datetime import datetime

from dotenv import load_dotenv

from es_client import create_chat_indexes

load_dotenv()
logging.basicConfig(filename="logs/es_load.log")

ES_ENDPOINT = os.getenv("ES_ENDPOINT")
JOURNAL = os.getenv("JOURNAL_PATH")
EMBEDDINGS = os.getenv("EMBEDDINGS_PATH")

def wait_for_elasticsearch() -> None:
    """ Waits for successful connection to Elasticsearch. """
    for _ in range(30):
        try:
            r = requests.get(ES_ENDPOINT)
            print(r.status_code)
            if r.status_code == 200:
                print("✅ Elasticsearch is up")
                return
        except requests.ConnectionError:
            pass
        print("⏳ Waiting for Elasticsearch...")
        time.sleep(2)
    raise RuntimeError("‼️ Elasticsearch startup timed out!")

def extract_transcription(text: str) -> str:
    """ Given a markdown file, extracts anything within the Transcription header """
    match = re.search(r'### Transcription\s*(.*?)\s*(^###|\Z)', text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""

def extract_tags(text: str) -> list[str]:
    """ Extract all tags from a markdown doc (anything starting with `#`) """
    return list(set(re.findall(r'#\w+', text)))

def index_embeddings():
    with open(EMBEDDINGS, 'r') as f:
        embeddings = json.load(f)

    for filename, embedding in embeddings.items():
        _filename = os.path.basename(filename)
        title = os.path.splitext(_filename)[0]

        # search for doc by title
        search_url = f"{ES_ENDPOINT}/journals/_search"
        query = {
            "query": {
                "term": {
                    "title.keyword": title
                }
            }
        }
        response = requests.get(search_url, json=query)
        hits = response.json().get("hits", {}).get("hits", [])
        if not hits:
            logging.info(f"No ES doc found for {title}")
            continue

        for doc in hits:
            doc_id = doc["_id"]
            update_url = f"{ES_ENDPOINT}/journals/_update/{doc_id}"
            update_body = {
                "doc": {
                    "embedding": embedding
                }
            }
            update_response = requests.post(update_url, json=update_body)
            if update_response.status_code == 200:
                print(f" Added embedding to {doc_id}")
            else:
                print(f"Failed to update {doc_id}")

def index_notes():
    for path in glob.glob(f"{JOURNAL}/**/*.md", recursive=True):
        filename = os.path.basename(path)
        date_part = filename.replace(".md", "")

        # skip weekly notes
        if date_part.endswith("- Week"):
            logging.info(f"⏩ Skipping file: {filename}")
            continue

        # handle doubleheaders
        date_parts = date_part.split('_')
        try:
            dates = [datetime.strptime(d, "%m-%d-%Y") for d in date_parts]
        except ValueError:
            logging.warning(f"Skipping file with invalid date format: {filename}")
            continue

        # get content from note
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        transcription = extract_transcription(content)
        tags = extract_tags(content)

        # prepare data to send
        for date in dates:
            doc = {
                "date": date.strftime("%Y-%m-%d"),
                "title": date_part,
                "text": transcription,
                "tags": tags,
            }

        # index the doc
        doc_id = date_part
        res = requests.post(f"{ES_ENDPOINT}/journals/_doc/{doc_id}", json=doc)
        print(f"📥 Indexed {filename}: {res.status_code}")

if __name__ == "__main__":
    wait_for_elasticsearch()
    index_notes()
    index_embeddings()
    create_chat_indexes()
