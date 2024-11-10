import logging
from navigation import *
from transcribe import *

logging.basicConfig(level=logging.INFO, filename='x.log')

files = crawl_journal_entries("data/10-2024")
print(files)
