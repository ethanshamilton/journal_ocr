# ingestion_ops.py
# functions for handling batch ingestion

import os
import json
import time
import asyncio
import logging

from core.settings import settings
from core.ingest import extract_transcription
from core.navigation import strip_frontmatter, compute_content_hash
from core.llm import get_embedding
from core.log_config import setup_logging
from pipeline.transcription import (
    encode_entry, transcribe_images, insert_transcription,
    update_frontmatter_field
)

logger = setup_logging()

def _append_embedding(embeddings_path: str, file_path: str, embedding: list[float]) -> None:
    entry = {"path": file_path, "embedding": embedding}
    with open(embeddings_path, 'a') as f:
        f.write(json.dumps(entry) + "\n")

async def transcribe_docs(files: list[tuple[str, str]], tags: str) -> None:
    logger.info("transcription_beginning", extra={
        "metrics": {
            "input_doc_count": len(files)
        }
    })
    start = time.perf_counter()

    semaphore = asyncio.Semaphore(5)
    await asyncio.gather(*[transcribe_single_doc(semaphore, f, tags) for f in files])

    logger.info("transcription_completed", extra={
        "metrics": {
            "input_doc_count": len(files),
            "elapsed_time_ms": (time.perf_counter() - start) * 1000
        }
    })

async def embed_docs(files: list[str], embeddings_path: str | None = None) -> None:
    logger.info("embedding_beginning", extra={
        "metrics": {
            "input_doc_count": len(files)
        }
    })
    start = time.perf_counter()

    semaphore = asyncio.Semaphore(5)
    embeddings_file = embeddings_path or settings.file_storage.embedding_storage_path
    if not os.path.exists(embeddings_file):
        open(embeddings_file, 'w').close()
    await asyncio.gather(*[embed_single_doc(semaphore, f, embeddings_file) for f in files])

    logger.info("embedding_completed", extra={
        "metrics": {
            "input_doc_count": len(files),
            "elapsed_time_ms": (time.perf_counter() - start) * 1000
        }
    })

async def transcribe_single_doc(
    semaphore: asyncio.Semaphore,
    file: tuple[str, str],
    tags: str
) -> None:
    logger.debug(f"transcribing {file}")
    async with semaphore:
        start = time.perf_counter()
        images = encode_entry(file[0])
        transcription = await transcribe_images(images, tags)
        insert_transcription(file[1], transcription)
        logger.info(f"transcription completed for ...{file[0][-25:]}", extra={
            "metrics": {"time_elapsed_ms": (time.perf_counter() - start) * 1000}
        })

async def embed_single_doc(
    semaphore: asyncio.Semaphore,
    file: str,
    embeddings_path: str
) -> None:

    logger.debug(f"embedding {file}")
    async with semaphore:
        start = time.perf_counter()
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        transcription = extract_transcription(content)
        embedding = await get_embedding(transcription)
        if embedding is None:
            raise ValueError(f"No embedding created for {file}")
        update_frontmatter_field(file, "embedding", "True")
        _append_embedding(embeddings_path, file, embedding)
        logger.info(f"embedding completed for ...{file[-25:]}", extra={
            "metrics": {"time_elapsed_ms": (time.perf_counter() - start) * 1000}
        })

async def embed_evergreen_docs(files: list[str], embeddings_path: str | None = None) -> None:
    logger.info("evergreen_embedding_beginning", extra={
        "metrics": {"input_doc_count": len(files)}
    })
    start = time.perf_counter()

    semaphore = asyncio.Semaphore(5)
    embeddings_file = embeddings_path or settings.file_storage.embedding_storage_path
    if not os.path.exists(embeddings_file):
        open(embeddings_file, 'w').close()
    await asyncio.gather(*[embed_single_evergreen(semaphore, f, embeddings_file) for f in files])

    logger.info("evergreen_embedding_completed", extra={
        "metrics": {
            "input_doc_count": len(files),
            "elapsed_time_ms": (time.perf_counter() - start) * 1000
        }
    })

async def embed_single_evergreen(
    semaphore: asyncio.Semaphore,
    file: str,
    embeddings_path: str
) -> None:
    logger.debug(f"embedding evergreen {file}")
    async with semaphore:
        start = time.perf_counter()
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        body = strip_frontmatter(content)
        content_hash = compute_content_hash(body)

        embedding = await get_embedding(body)
        if embedding is None:
            raise ValueError(f"No embedding created for evergreen {file}")

        update_frontmatter_field(file, "embedding", "True")
        update_frontmatter_field(file, "content_hash", content_hash)
        _append_embedding(embeddings_path, file, embedding)

        logger.info(f"evergreen embedding completed for ...{file[-25:]}", extra={
            "metrics": {"time_elapsed_ms": (time.perf_counter() - start) * 1000}
        })
