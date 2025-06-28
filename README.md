# journal_ocr
This vault contains code for transcribing my journals and interacting with the data. 

<img src="_docs/journal-rag-img.png"></img>

## Quick Start
1. `./launch.sh` - runs transcription and embedding pipelines, starts docker network, and loads data.
2. `cd ui && run npm dev` - starts frontend. I haven't integrated this with docker yet. 
3. `uv run uvicorn src.api:app --reload` - starts backend API. Also not integrated with docker yet. 

## Current Capabilities
- Checks configured data folder for the journal and makes sure everything is transcribed and embedded, then loads it to elasticsearch. 
- Runs a basic similarity search RAG across journal entries and uses that to generate an LLM response. 
- Shows LLM response along with retrieved entries in frontend.

## Roadmap
- Add recent entries retrieval based on data. 
- Add tag retrieval based on entry tags. 
- Add LLM router ("agent") that can determine which type of retrieval to use based on user query. 
- Add options to frontend to allow selection of different models. 
