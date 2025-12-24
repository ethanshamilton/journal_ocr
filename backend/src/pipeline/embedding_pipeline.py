# contains pipeline code for embedding journal entries on startup
import os
import json
import asyncio
import argparse

from dotenv import load_dotenv
from rich.progress import (
    Progress, SpinnerColumn,
    BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn
)

from core import ingest as i
from core import navigation as nav
from core.llm import get_embedding
from pipeline.transcription import update_frontmatter_field

load_dotenv()


async def run_embedding(files: list[str], embeddings: dict, embeddings_path: str):
    """Run embedding on a list of files."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn()
    ) as progress:

        task = progress.add_task("Embedding...", total=len(files))

        for entry in files:
            with open(entry, 'r', encoding='utf-8') as file:
                content = file.read()
            transcription = i.extract_transcription(content)
            embedding = await get_embedding(transcription)
            update_frontmatter_field(entry, "embedding", "True")
            embeddings[entry] = embedding
            progress.update(task, advance=1)

    # save embeddings
    with open(embeddings_path, "w") as f:
        json.dump(embeddings, f)


def main():
    parser = argparse.ArgumentParser(description="Run journal embedding")

    parser.add_argument(
        "--mode",
        choices=["test", "live"],
        default="test",
        help="Run mode: test or real"
    )

    args = parser.parse_args()

    if args.mode == "test":
        root_dir = "data/test_data"
        embeddings_path = "data/embeddings.json"
    if args.mode == "live":
        root_dir = os.getenv("JOURNAL_PATH")
        embeddings_path = os.getenv("EMBEDDINGS_PATH")

    if os.path.exists(embeddings_path):
        with open(embeddings_path, 'r') as f:
            embeddings = json.load(f)
    else:
        embeddings = {}

    files = nav.crawl_journal_entries(root_dir)['to_embed']
    print(files)

    # embed files
    asyncio.run(run_embedding(files, embeddings, embeddings_path))


if __name__ == "__main__":
    main()
