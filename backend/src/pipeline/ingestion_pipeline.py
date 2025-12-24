# ingestion_pipeline.py
# unified transcription and embedding pipeline that pulls data
# from onedrive and prepares it for use

import asyncio

from core.navigation import crawl_journal_entries, extract_tags
from core.settings import settings
from pipeline.ingestion_ops import transcribe_docs, embed_docs

async def main():
    # get docs for processing
    files = crawl_journal_entries(settings.lancedb.journal_storage_path)
    tags = extract_tags(settings.lancedb.journal_storage_path)

    transcriptions = transcribe_docs(files.to_transcribe, tags)
    embeddings = embed_docs(files.to_embed)

    pass

if __name__ == "__main__":
    asyncio.run(main())
