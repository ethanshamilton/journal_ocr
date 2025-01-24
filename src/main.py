import logging
from navigation import *
from transcribe import *

with open('x.log', 'w') as f:
    f.write('')
logging.basicConfig(level=logging.INFO, filename='x.log')

SOURCE_DATA = "data/sample_data"
TEST_DATA = "data/test_data"

# prepare data for testing
duplicate_folder(SOURCE_DATA, TEST_DATA)
# prepare list of files for transcription
files = crawl_journal_entries(TEST_DATA)
# transcribe files
for entry, file in files:
    images = encode_entry(entry)
    transcriptions = transcribe_images(images)
    print(transcriptions)
    insert_transcription(file, transcriptions)
