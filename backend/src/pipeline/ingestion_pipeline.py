# ingestion_pipeline.py
# unified transcription and embedding pipeline that pulls data
# from onedrive and prepares it for use

import asyncio

from core.navigation import crawl_journal_entries, crawl_evergreen_entries, extract_tags
from core.settings import settings
from pipeline.ingestion_ops import transcribe_docs, embed_docs, embed_evergreen_docs

async def main():
    # get docs for processing
    files = crawl_journal_entries(settings.file_storage.journal_storage_path)
    tags = extract_tags(settings.file_storage.journal_storage_path)

    transcriptions = await transcribe_docs(files.to_transcribe, tags)
    embeddings = await embed_docs(files.to_embed)

    # evergreen entries
    evergreen_files = crawl_evergreen_entries(settings.file_storage.evergreen_storage_path)
    if evergreen_files:
        await embed_evergreen_docs(evergreen_files)

if __name__ == "__main__":
    asyncio.run(main())
