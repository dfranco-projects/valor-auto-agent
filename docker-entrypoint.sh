#!/usr/bin/env bash
set -euo pipefail

# backend owns the graph/db; run it in the background
# --no-sync: the image is already built, don't re-resolve deps at startup
uv run --no-sync uvicorn backend.main:app --app-dir src --host 0.0.0.0 --port 8000 &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT

# wait for the backend to accept connections before starting the ui (slim has no curl,
# so probe the port with bash /dev/tcp)
echo "waiting for backend on :8000 ..."
for _ in $(seq 1 120); do
    if (exec 3<>/dev/tcp/127.0.0.1/8000) 2>/dev/null; then
        exec 3>&- 3<&-
        echo "backend ready"
        break
    fi
    sleep 0.5
done

# the next.js standalone server in the foreground keeps the container alive
# (HOSTNAME=0.0.0.0 and PORT=8501 are set in the image env)
exec node frontend-web/server.js
