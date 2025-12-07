# lancedb.py
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

import lancedb
import polars as pl
from dotenv import load_dotenv

from ingest import load_chats_to_dfs, load_notes_to_df
from models import Entry

load_dotenv()
logger = logging.getLogger(__name__)

class LocalLanceDB:
    def __init__(self, path):
        self.path = path
        self.db = lancedb.connect(path)

    def startup_ingest(self) -> None:
        logging.info("[lancedb] beginning startup ingestion")
        chats = os.getenv("CHATS_LOCAL_PATH")
        embeddings = os.getenv("EMBEDDINGS_PATH")
        journal = os.getenv("JOURNAL_PATH")

        if not (chats and embeddings and journal):
            raise FileNotFoundError("ensure chats, embeddings, and journal data are available")

        # load to dataframes
        threads_df, messages_df = load_chats_to_dfs(chats)
        journal_df = load_notes_to_df(embeddings, journal)

        # journal: always overwrite (source of truth is markdown files)
        self.db.create_table("journal", data=journal_df, mode="overwrite")
        
        # threads/messages: only create if not exists (source of truth is the db)
        existing_tables = self.db.table_names()
        if "threads" not in existing_tables:
            self.db.create_table("threads", data=threads_df)
            logging.info("[lancedb] created threads table from chats.json")
        if "messages" not in existing_tables:
            self.db.create_table("messages", data=messages_df)
            logging.info("[lancedb] created messages table from chats.json")
        
        # create indexes
        self.db.open_table("journal").create_index(
                metric="cosine",
                vector_column_name="embedding"
            )

    ### search and retrieval

    def get_recent_entries(self, n: int = 7) -> list[Entry]:
        table = self.db.open_table("journal")
        entries_df = pl.from_arrow(table.to_arrow()).sort("date", descending=True).head(n)
        return self.df_to_entries(entries_df)

    def get_similar_entries(self, _embedding: list[float], n: int = 5) -> list[(Entry, float)]:
        table = self.db.open_table("journal")
        entries_df = table.search(_embedding).limit(n).to_polars().sort("_distance", descending=False)
        entries = self.df_to_entries(entries_df)
        distances = entries_df["_distance"].to_list()
        return list(zip(entries, distances))

    def get_entries_by_date_range(self, start_date: str, end_date: str, n: int = None) -> list[Entry]:
        table = self.db.open_table("journal")
        entries_df = table.search().where(f"date >= '{start_date}' AND date <= '{end_date}'").to_polars()
        return self.df_to_entries(entries_df)

    def df_to_entries(self, df: pl.DataFrame) -> list[Entry]:
        return [
            Entry(
                date=row["date"],
                title=row["title"],
                text=row["text"],
                tags=row["tags"],
                embedding=row["embedding"]
            ) for row in df.iter_rows(named=True)
        ]

    ### thread management

    def create_thread(self, title: Optional[str] = None, initial_message: Optional[str] = None) -> dict:
        """Create a new thread"""
        thread_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        thread_doc = {
            "thread_id": thread_id,
            "title": title or f"Chat {now.strftime('%Y-%m-%d %H:%M')}",
            "tags": [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        table = self.db.open_table("threads")
        table.add([thread_doc])
        
        if initial_message:
            self.save_message(thread_id, "user", initial_message)
        
        return thread_doc

    def get_threads(self) -> list[dict]:
        """Get all threads sorted by updated_at desc"""
        table = self.db.open_table("threads")
        df = pl.from_arrow(table.to_arrow()).sort("updated_at", descending=True)
        return df.to_dicts()

    def get_thread(self, thread_id: str) -> Optional[dict]:
        """Get a specific thread by id"""
        table = self.db.open_table("threads")
        df = pl.from_arrow(table.to_arrow()).filter(pl.col("thread_id") == thread_id)
        if df.is_empty():
            return None
        return df.to_dicts()[0]

    def update_thread(self, thread_id: str, updates: dict) -> bool:
        """Update a thread (e.g., title)"""
        existing = self.get_thread(thread_id)
        if not existing:
            return False
        
        existing.update(updates)
        existing["updated_at"] = datetime.utcnow().isoformat()
        
        table = self.db.open_table("threads")
        table.delete(f"thread_id = '{thread_id}'")
        table.add([existing])
        return True

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and all its messages"""
        try:
            threads_table = self.db.open_table("threads")
            messages_table = self.db.open_table("messages")
            
            threads_table.delete(f"thread_id = '{thread_id}'")
            messages_table.delete(f"thread_id = '{thread_id}'")
            return True
        except Exception:
            return False

    ### message management

    def get_thread_messages(self, thread_id: str) -> list[dict]:
        """Get all messages for a thread sorted by timestamp"""
        table = self.db.open_table("messages")
        df = pl.from_arrow(table.to_arrow()).filter(pl.col("thread_id") == thread_id)
        df = df.sort("timestamp")
        return df.to_dicts()

    def save_message(self, thread_id: str, role: str, content: str) -> dict:
        """Save a message to a thread"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        message_doc = {
            "message_id": message_id,
            "thread_id": thread_id,
            "timestamp": now.isoformat(),
            "role": role,
            "content": content
        }
        
        messages_table = self.db.open_table("messages")
        messages_table.add([message_doc])
        
        # update thread's updated_at
        self.update_thread(thread_id, {})
        
        return message_doc
