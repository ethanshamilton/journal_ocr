# contains pipeline code for embedding journal entries on startup
import os
import argparse

from openai import OpenAI
from dotenv import load_dotenv
from rich.progress import (
    Progress, SpinnerColumn, 
    BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn
)

import loader as l
import navigation as nav

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

TEST_DATA = "data/test_data"
JOURNAL = os.getenv("JOURNAL_PATH")

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
        root_dir = TEST_DATA
    if args.mode == "live":
        root_dir = JOURNAL

    files = nav.crawl_journal_entries(root_dir)['to_embed']
    print(files)

    # embed files
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
            transcription = l.extract_transcription(content)
            progress.console.print(transcription)
            progress.update(task, advance=1)

if __name__ == "__main__":
    main()                
