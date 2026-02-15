# lancedb_client.py
import uuid
import logging
from datetime import datetime
from typing import Optional

import lancedb
import polars as pl
import pyarrow as pa

from core.ingest import load_chats_to_dfs, load_notes_to_df, load_evergreen_to_df
from core.models import Entry
from core.settings import settings

logger = logging.getLogger(__name__)


class AsyncLocalLanceDB:
    def __init__(self, path: str):
        self.path = path
        self.db: lancedb.AsyncConnection = None

    async def connect(self):
        """Initialize the async database connection."""
        self.db = await lancedb.connect_async(self.path)

    async def startup_ingest(self) -> None:
        logging.info("[lancedb] beginning startup ingestion")
        chats = settings.file_storage.chat_storage_path
        embeddings = settings.file_storage.embedding_storage_path
        journal = settings.file_storage.journal_storage_path
        evergreen = settings.file_storage.evergreen_storage_path

        if not (chats and embeddings and journal):
            raise FileNotFoundError("ensure chats, embeddings, and journal data are available")

        # load to dataframes
        threads_df, messages_df = load_chats_to_dfs(chats)
        journal_df = load_notes_to_df(embeddings, journal)

        # load evergreen entries and concatenate
        evergreen_df = load_evergreen_to_df(embeddings, evergreen)
        if len(evergreen_df) > 0:
            journal_df = pl.concat([journal_df, evergreen_df])
            logging.info(f"[lancedb] added {len(evergreen_df)} evergreen entries")

        # journal: always overwrite (source of truth is markdown files)
        await self.db.create_table("journal", data=journal_df, mode="overwrite")

        # threads/messages: only create if not exists (source of truth is the db)
        existing_tables = await self.db.table_names()
        if "threads" not in existing_tables:
            if threads_df is not None and len(threads_df) > 0:
                await self.db.create_table("threads", data=threads_df)
                logging.info("[lancedb] created threads table from chats.json")
            else:
                # Create empty table with schema
                threads_schema = pa.schema([
                    pa.field("thread_id", pa.string()),
                    pa.field("title", pa.string()),
                    pa.field("tags", pa.list_(pa.string())),
                    pa.field("created_at", pa.string()),
                    pa.field("updated_at", pa.string()),
                ])
                await self.db.create_table("threads", schema=threads_schema)
                logging.info("[lancedb] created empty threads table")
        if "messages" not in existing_tables:
            if messages_df is not None and len(messages_df) > 0:
                await self.db.create_table("messages", data=messages_df)
                logging.info("[lancedb] created messages table from chats.json")
            else:
                # Create empty table with schema
                messages_schema = pa.schema([
                    pa.field("message_id", pa.string()),
                    pa.field("thread_id", pa.string()),
                    pa.field("timestamp", pa.string()),
                    pa.field("role", pa.string()),
                    pa.field("content", pa.string()),
                ])
                await self.db.create_table("messages", schema=messages_schema)
                logging.info("[lancedb] created empty messages table")

        # create indexes
        journal_table = await self.db.open_table("journal")
        await journal_table.create_index(
            "embedding",
            config=lancedb.index.IvfPq(distance_type="cosine"),
        )

    ### search and retrieval

    async def get_recent_entries(self, n: int = 7) -> list[Entry]:
        table = await self.db.open_table("journal")
        arrow_table = await table.to_arrow()
        entries_df = pl.from_arrow(arrow_table).sort("date", descending=True).head(n)
        return self.df_to_entries(entries_df)

    async def get_similar_entries(self, _embedding: list[float], n: int = 5) -> list[tuple[Entry, float]]:
        table = await self.db.open_table("journal")
        search_result = await table.search(_embedding)
        entries_df = await search_result.limit(n).to_polars()
        entries_df = entries_df.sort("_distance", descending=False)
        entries = self.df_to_entries(entries_df)
        distances = entries_df["_distance"].to_list()
        return list(zip(entries, distances))

    async def get_entries_by_date_range(self, start_date: str, end_date: str, n: int = None) -> list[Entry]:
        table = await self.db.open_table("journal")
        entries_df = await table.search().where(f"date >= '{start_date}' AND date <= '{end_date}'").to_polars()
        return self.df_to_entries(entries_df)

    def df_to_entries(self, df: pl.DataFrame) -> list[Entry]:
        return [
            Entry(
                date=row["date"],
                title=row["title"],
                text=row["text"],
                tags=row["tags"],
                embedding=row["embedding"],
                entry_type=row.get("entry_type", "daily"),
            ) for row in df.iter_rows(named=True)
        ]

    ### thread management

    async def create_thread(self, title: Optional[str] = None, initial_message: Optional[str] = None) -> dict:
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

        table = await self.db.open_table("threads")
        await table.add([thread_doc])

        if initial_message:
            await self.save_message(thread_id, "user", initial_message)

        return thread_doc

    async def get_threads(self) -> list[dict]:
        """Get all threads sorted by updated_at desc"""
        table = await self.db.open_table("threads")
        arrow_table = await table.to_arrow()
        df = pl.from_arrow(arrow_table).sort("updated_at", descending=True)
        return df.to_dicts()

    async def get_thread(self, thread_id: str) -> Optional[dict]:
        """Get a specific thread by id"""
        table = await self.db.open_table("threads")
        arrow_table = await table.to_arrow()
        df = pl.from_arrow(arrow_table).filter(pl.col("thread_id") == thread_id)
        if df.is_empty():
            return None
        return df.to_dicts()[0]

    async def update_thread(self, thread_id: str, updates: dict) -> bool:
        """Update a thread (e.g., title)"""
        existing = await self.get_thread(thread_id)
        if not existing:
            return False

        existing.update(updates)
        existing["updated_at"] = datetime.utcnow().isoformat()

        table = await self.db.open_table("threads")
        await table.delete(f"thread_id = '{thread_id}'")
        await table.add([existing])
        return True

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a thread and all its messages"""
        try:
            threads_table = await self.db.open_table("threads")
            messages_table = await self.db.open_table("messages")

            await threads_table.delete(f"thread_id = '{thread_id}'")
            await messages_table.delete(f"thread_id = '{thread_id}'")
            return True
        except Exception:
            return False

    ### message management

    async def get_thread_messages(self, thread_id: str) -> list[dict]:
        """Get all messages for a thread sorted by timestamp"""
        table = await self.db.open_table("messages")
        arrow_table = await table.to_arrow()
        df = pl.from_arrow(arrow_table).filter(pl.col("thread_id") == thread_id)
        df = df.sort("timestamp")
        return df.to_dicts()

    async def save_message(self, thread_id: str, role: str, content: str) -> dict:
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

        messages_table = await self.db.open_table("messages")
        await messages_table.add([message_doc])

        # update thread's updated_at
        await self.update_thread(thread_id, {})

        return message_doc
