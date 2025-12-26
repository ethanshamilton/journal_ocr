# ingestion_ops.py
# functions for handling batch ingestion

import json
import asyncio

from core.settings import settings
from core.ingest import extract_transcription
from core.llm import get_embedding
from pipeline.transcription import (
    encode_entry, transcribe_images, insert_transcription,
    update_frontmatter_field
)

async def transcribe_docs(files: list[tuple[str, str]], tags: str) -> None:
    semaphore = asyncio.Semaphore(5)
    await asyncio.gather(*[transcribe_single_doc(semaphore, f, tags) for f in files], return_exceptions=True)

async def embed_docs(files: list[str], embeddings_path: str | None = None) -> None:
    semaphore = asyncio.Semaphore(5)
    embeddings_file = embeddings_path or settings.file_storage.embedding_storage_path
    await asyncio.gather(*[embed_single_doc(semaphore, f, embeddings_file) for f in files], return_exceptions=True)

async def transcribe_single_doc(
    semaphore: asyncio.Semaphore,
    file: tuple[str, str],
    tags: str
) -> None:
    async with semaphore:
        images = encode_entry(file[0])
        transcription = await transcribe_images(images, tags)
        insert_transcription(file[1], transcription)

async def embed_single_doc(
    semaphore: asyncio.Semaphore,
    file: str,
    embeddings_path: str
) -> None:

    def append_embedding(embeddings_path: str, file_path: str, embedding: list[float]) -> None:
        entry = {"path": file_path, "embedding": embedding}
        with open(embeddings_path, 'a') as f:
            f.write(json.dumps(entry) + "\n")

    async with semaphore:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        transcription = extract_transcription(content)
        embedding = await get_embedding(transcription)
        update_frontmatter_field(file, "embedding", "True")
        append_embedding(embeddings_path, file, embedding)
