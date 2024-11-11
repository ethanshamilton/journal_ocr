import logging
from navigation import *
from transcribe import *

logging.basicConfig(level=logging.INFO, filename='x.log')

files = crawl_journal_entries("data/10-2024")
for entry, file in files:
    images = encode_entry(entry)
    transcriptions = transcribe_images(images)
    append_to_markdown(file, transcriptions)
