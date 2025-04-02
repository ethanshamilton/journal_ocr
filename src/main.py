import logging
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

# prepare data for testing
nav.duplicate_folder(SOURCE_DATA, TEST_DATA)
# prepare list of files for transcription
files = nav.crawl_journal_entries(TEST_DATA)
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
        transcriptions = tx.transcribe_images(images)
        progress.console.print(f"transcription of {file} complete")
        tx.insert_transcription(file, transcriptions)
        progress.update(task, advance=1)
