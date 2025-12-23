#!/bin/bash

# Exit immediately if any command fails
set -e

export PYTHONPATH=src

echo ""
echo "🔍 Running tests..."
echo ""

uv run pytest

echo ""
echo "🚀 Running transcription pipeline in test mode..."
echo ""

uv run python src/transcription_pipeline.py --mode test

echo ""
echo "🕸️ Running embedding pipeline in test mode..."
echo ""

uv run python src/embedding_pipeline.py --mode test

echo ""
