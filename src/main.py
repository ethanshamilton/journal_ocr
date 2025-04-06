import logging
import argparse
import navigation as nav
import transcribe as tx
from rich.progress import (
    Progress, SpinnerColumn, 
    BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn
)

with open('x.log', 'w') as f:
    f.write('')
logging.basicConfig(level=logging.INFO, filename='x.log')

SOURCE_DATA = "data/sample_data"
TEST_DATA = "data/test_data"
JOURNAL = '/Users/hamiltones/Documents/Journal/Daily Pages'

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
    files = nav.crawl_journal_entries(root_dir)

    # get tags
    tags = nav.extract_tags(root_dir)

    # transcribe files
    with Progress(
        SpinnerColumn(), 
        TextColumn("[progress.description]{task.description}"), 
        BarColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn()
    ) as progress:
        
        task = progress.add_task("Processing...", total=len(files))

        for entry, file in files:
            images = tx.encode_entry(entry)
            transcriptions = tx.transcribe_images(images, tags)
            progress.console.print(f"transcription of {file} complete")
            tx.insert_transcription(file, transcriptions)
            progress.update(task, advance=1)

if __name__ == "__main__":
    main()
