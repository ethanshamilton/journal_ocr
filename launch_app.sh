#!/bin/bash

# Integrated app launcher
# 1. Start frontend (shows loading screen)
# 2. Run ingestion pipeline (blocking)
# 3. Start backend (frontend detects ready status)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_PID=""
BACKEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down..."

    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
        echo "Frontend stopped"
    fi

    if [ -n "$BACKEND_PID" ]; then
        # Kill child processes first (uvicorn's server process), then the reloader
        pkill -P $BACKEND_PID 2>/dev/null || true
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
        echo "Backend stopped"
    fi

    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "📖 Starting Journal App"
echo ""

# 1. Start frontend in background
echo "Starting frontend..."
cd "$SCRIPT_DIR/ui"
npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo "Frontend started (PID: $FRONTEND_PID)"
echo ""

# 2. Run ingestion pipeline (blocking)
echo "Running ingestion pipeline..."
cd "$SCRIPT_DIR/backend"
uv run python -m pipeline.ingestion_pipeline
cd "$SCRIPT_DIR"

echo ""
echo "Pipeline complete"
echo ""

# 3. Start backend in background
echo "Starting backend..."
cd "$SCRIPT_DIR/backend"
uv run uvicorn backend.api:app --reload &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "Waiting for backend to initialize..."
while true; do
    STATUS=$(curl -s http://127.0.0.1:8000/status 2>/dev/null | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" = "ready" ]; then
        break
    fi
    sleep 0.5
done

echo ""
echo "App ready at http://localhost:5173"
echo "Press Ctrl+C to stop"
echo ""

# Wait for background processes
wait
