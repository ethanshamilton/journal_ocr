#!/bin/bash

# Exit immediately if any command fails
set -e

echo ""
echo "🔍 Running tests..."
echo ""

pytest

echo ""
echo "🚀 Running transcription pipeline in test mode..."
echo ""

python src/transcription_pipeline.py --mode test

echo ""
echo "🕸️ Running embedding pipeline in test mode..."

python src/embedding_pipeline.py --mode test
