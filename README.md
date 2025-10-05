# journal_ocr
This vault contains code for transcribing my journals and interacting with the data. 

<img src="_docs/journal-rag-img.png"></img>

## Quick Start
1. `./launch.sh` - runs transcription and embedding pipelines, starts docker network, and loads data.
2. `cd ui && run npm dev` - starts frontend. I haven't integrated this with docker yet. 
3. `cd src && uv run uvicorn api:app --reload` - starts backend API. Also not integrated with docker yet. 

## Current Capabilities
- Checks configured data folder for the journal and makes sure everything is transcribed and embedded, then loads it to elasticsearch. 
- Classifies query intent and selects the best retrieval mechanism from options such as vector RAG or recent entries. 
- Generates an LLM response based on the retrieved entries. 
- Shows LLM response along with retrieved entries in frontend.

## Roadmap
- Add tag retrieval based on entry tags. 
- Add specific date retrieval i.e. last month, last year, September 2021...
- Add frontend and backend into docker network.
- Implement chat history. 
    - Start just with per-session chat. Include a button to clear history. 
    - Store chats in elasticsearch so they can be loaded or searched later. 
