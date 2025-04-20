# journal_ocr
This vault contains code for transcribing my journals and interacting with the data. 

Currently, `main.py` contains the code for transcribing the journals. It can be run on its own
via `test_run.sh` or `run.sh`. Sorry there is no data in the repo but the data is sensitive, I may
add example data in the future. 

There is also an elasticsearch container setup. I am working on adding the ability to automate
journal transcription and loading when starting the container. 

Once that is done, I'm going to write queries of elasticsearch that provide retrieval mechanisms such
as date queries and semantic similarity. I may then add a simple frontend, we'll see. 
