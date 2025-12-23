#!/bin/bash

echo ""
echo "🚀 Running main.py..."
echo ""

uv run python -m backend.transcription_pipeline --mode live
