# lancedb.py
import os
import logging

import lancedb
import polars as pl
from dotenv import load_dotenv

from ingest import load_chats_to_dfs, load_notes_to_df

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

    def get_recent_entries(self, n: int = 7) -> pl.DataFrame:
        table = self.db.open_table("journal")
        df = pl.from_arrow(table.to_arrow())
        return df.sort("date", descending=True).head(n)

    def get_similar_entries(self, embedding: list[float], n: int = 5) -> pl.DataFrame:
        table = self.db.open_table("journal")
        return table.search(embedding).limit(n).to_polars().sort("_distance", descending=False)
