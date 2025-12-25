# ingestion_ops.py
# functions for handling batch ingestion

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

async def embed_docs(files: list[str]) -> None:
    semaphore = asyncio.Semaphore(5)
    return None

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
    embeddings_dict: dict
) -> None:
    async with semaphore:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        transcription = extract_transcription(content)
        embedding = await get_embedding(transcription)
        update_frontmatter_field(file, "embedding", "True")
        embeddings_dict[file] = embedding # I don't think this will work right
        # the problem is that we would need to pass embeddings_dict back and forth
    return None
