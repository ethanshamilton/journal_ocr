#!/bin/bash

echo ""
echo "📖 Opening Journal"
echo ""

python src/transcription_pipeline.py --mode live

echo ""

python src/embedding_pipeline.py --mode live

docker compose up -d

python src/loader.py --mode live
