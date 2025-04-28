#!/bin/bash

# Exit immediately if any command fails
set -e

echo ""
echo "🔍 Running tests..."
echo ""

pytest

echo ""
echo "🚀 Running main.py in test mode..."
echo ""

python src/transcription_pipeline.py --mode test
