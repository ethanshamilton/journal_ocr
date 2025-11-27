#!/bin/bash

echo ""
echo "📖 Opening Journal"
echo ""

uv run src/transcription_pipeline.py --mode live

echo ""

uv run src/embedding_pipeline.py --mode live

docker compose up -d

uv run src/ingest.py --mode live
