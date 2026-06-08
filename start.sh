#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Load env vars
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | xargs)
fi

echo "Starting AI Chatbot SaaS..."

# Start backend API in background
cd "$ROOT/backend"
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running at http://localhost:8000 (PID $BACKEND_PID)"

# Start Streamlit dashboard
cd "$ROOT/dashboard"
streamlit run app.py --server.port 8501 &
DASH_PID=$!
echo "Dashboard running at http://localhost:8501 (PID $DASH_PID)"

echo ""
echo "Press Ctrl+C to stop both services."
trap "kill $BACKEND_PID $DASH_PID 2>/dev/null; echo 'Stopped.'" SIGINT SIGTERM

wait
