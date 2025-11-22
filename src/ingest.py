# ingest.py
# for loading data into things
import os
import re
import json
import glob
import logging
from datetime import datetime

import polars as pl
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(filename="logs/loader.log")

def extract_transcription(text: str) -> str:
    """ Given a markdown file, extracts anything within the Transcription header """
    match = re.search(r'### Transcription\s*(.*?)\s*(^###|\Z)', text, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""

def extract_tags(text: str) -> list[str]:
    """ Extract all tags from a markdown doc (anything starting with `#`) """
    return list(set(re.findall(r'#\w+', text)))

def get_date_part(filepath):
    return os.path.basename(filepath).replace(".md", "")

def load_chats_to_dfs(chats_file: str) -> (pl.DataFrame, pl.DataFrame):
    """ Loads chat history from local JSON export into separate Polars DataFrames for threads and messages. """
    if not os.path.exists(chats_file):
        logging.error(f"Chats file not found at {chats_file}")
        return None, None

    with open(chats_file, 'r') as f:
        data = json.load(f)

    threads = data.get("threads", [])
    messages = data.get("messages", [])

    threads_df = pl.DataFrame(threads)
    messages_df = pl.DataFrame(messages)

    return threads_df, messages_df

def load_notes_to_df(embeddings_path: str, notes_dir: str):
    # Load embeddings map
    embeddings_map = {}
    if os.path.exists(embeddings_path):
        try:
            with open(embeddings_path, 'r') as f:
                data = json.load(f)
                for k, v in data.items():
                    embeddings_map[get_date_part(k)] = v
        except Exception as e:
            logging.error(f"Failed to load embeddings: {e}")

    rows = []
    missing_embeddings = 0

    for path in glob.glob(f"{notes_dir}/**/*.md", recursive=True):
        date_part = get_date_part(path)

        # skip weekly notes
        if date_part.endswith("- Week"):
            logging.info(f"Skipping file: {date_part}")
            continue

        # handle doubleheaders
        date_parts = date_part.split('_')
        try:
            dates = [datetime.strptime(d, "%m-%d-%Y") for d in date_parts]
        except ValueError:
            logging.warning(f"Skipping file with invalid date format: {date_part}")
            continue

        # get content from note
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        transcription = extract_transcription(content)
        tags = extract_tags(content)

        # prepare data rows
        for date in dates:
            if date_part not in embeddings_map:
                logging.warning(f"no embedding for {date_part}")
                missing_embeddings += 1
                continue
            
            row = {
                "date": date.strftime("%Y-%m-%d"),
                "title": date_part,
                "text": transcription,
                "tags": tags,
                "embedding": embeddings_map[date_part]
            }
            rows.append(row)

    # Create DataFrame
    df = pl.DataFrame(rows)
    logging.info(f"Number of missing embeddings: {missing_embeddings}")
    return df

# if __name__ == "__main__":
#     # wait_for_elasticsearch()
#     # threads_df, messages_df = load_chats_to_dfs()
#     # notes = load_notes_to_df()
#     # create_chat_indexes()
