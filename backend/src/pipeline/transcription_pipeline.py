import os
import asyncio
import logging
import argparse
from rich.progress import (
    Progress, SpinnerColumn,
    BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn
)
from dotenv import load_dotenv

from core import navigation as nav
from pipeline import transcription as t

load_dotenv()

with open('x.log', 'w') as f:
    f.write('')
logging.basicConfig(level=logging.INFO, filename='x.log')

SOURCE_DATA = "data/sample_data"
TEST_DATA = "data/test_data"
JOURNAL = os.getenv("JOURNAL_PATH")


async def run_transcription(files: list[tuple[str, str]], tags: str):
    """Run transcription on a list of files."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn()
    ) as progress:

        task = progress.add_task("Transcribing...", total=len(files))

        for entry, file in files:
            images = t.encode_entry(entry)
            transcriptions = await t.transcribe_images(images, tags)
            progress.console.print(f"transcription of {file} complete")
            t.insert_transcription(file, transcriptions)
            progress.update(task, advance=1)


def main():
    parser = argparse.ArgumentParser(description="Run journal OCR")

    parser.add_argument(
        "--mode",
        choices=["test", "live"],
        default="test",
        help="Run mode: test or real."
    )

    args = parser.parse_args()

    if args.mode == "test":
        nav.duplicate_folder(SOURCE_DATA, TEST_DATA)
        root_dir = TEST_DATA
    if args.mode == "live":
        root_dir = JOURNAL

    # prepare list of files for transcription
    files = nav.crawl_journal_entries(root_dir)['to_transcribe']

    # get tags
    tags = nav.extract_tags(root_dir)

    # transcribe files
    asyncio.run(run_transcription(files, tags))


if __name__ == "__main__":
    main()
