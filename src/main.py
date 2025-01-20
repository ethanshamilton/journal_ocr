import logging
from src.navigation import *
from src.transcribe import *

with open('x.log', 'w') as f:
    f.write('')
logging.basicConfig(level=logging.INFO, filename='x.log')

files = crawl_journal_entries("data/10-2024")
for entry, file in files:
    images = encode_entry(entry)
    transcriptions = transcribe_images(images)
    print(transcriptions)
    # append_to_markdown(file, transcriptions)
