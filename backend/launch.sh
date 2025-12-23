#!/bin/bash

echo ""
echo "📖 Opening Journal"
echo ""

uv run python -m backend.transcription_pipeline --mode live

echo ""

uv run python -m backend.embedding_pipeline --mode live

docker compose up -d

uv run python -m backend.ingest --mode live
