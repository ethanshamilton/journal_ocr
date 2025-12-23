#!/bin/bash

# Exit immediately if any command fails
set -e

echo ""
echo "🔍 Running tests..."
echo ""

uv run pytest

echo ""
echo "🚀 Running transcription pipeline in test mode..."
echo ""

uv run python -m backend.transcription_pipeline --mode test

echo ""
echo "🕸️ Running embedding pipeline in test mode..."
echo ""

uv run python -m backend.embedding_pipeline --mode test

echo ""
