# lancedb.py
import os
import logging

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

        if not chats and embeddings and journal:
            raise FileNotFoundError("ensure chats, embeddings, and journal data are available")

        # load to dataframes
        threads_df, messages_df = load_chats_to_dfs(chats)
        journal_df = load_notes_to_df(embeddings, journal)

        # create tables
        self.db.create_table("threads", data=threads_df, mode="overwrite")
        self.db.create_table("messages", data=messages_df, mode="overwrite")
        self.db.create_table("journal", data=journal_df, mode="overwrite")
        
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
