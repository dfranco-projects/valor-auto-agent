#!/usr/bin/env bash
set -euo pipefail

# backend owns the graph/db; run it in the background
# --no-sync: the image is already built, don't re-resolve deps at startup
uv run --no-sync uvicorn backend.main:app --app-dir src --host 0.0.0.0 --port 8000 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT

# frontend in the foreground keeps the container alive
uv run --no-sync streamlit run src/frontend/app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true
