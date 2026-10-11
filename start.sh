#!/usr/bin/env bash
set -eo pipefail

echo "=========================================================="
echo " Starting ICT Scanner & Dashboard (24/7 Production Mode) "
echo "=========================================================="

# 1. Ensure required data directories exist
mkdir -p data data/charts /app/data /app/data/charts 2>/dev/null || true

# 2. Port and Host Configuration
export HOST="${HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export BACKEND_INTERNAL_URL="${BACKEND_INTERNAL_URL:-http://127.0.0.1:${BACKEND_PORT}}"
export MPLBACKEND="${MPLBACKEND:-Agg}"
export PYTHONUNBUFFERED=1

echo "[Config] Host: ${HOST}"
echo "[Config] Backend Port: ${BACKEND_PORT}"
echo "[Config] Frontend Port: ${FRONTEND_PORT}"
echo "[Config] Backend Internal URL: ${BACKEND_INTERNAL_URL}"

# 3. Database Migration
echo "[Database] Running database migrations..."
if [ -f "alembic.ini" ]; then
    alembic upgrade head || echo "[Database] Migration warning (skipping if up to date or already initialized)"
fi

# 4. Graceful Shutdown Signal Handler
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "[Shutdown] Caught termination signal. Gracefully stopping services..."
    if [ -n "$FRONTEND_PID" ]; then
        echo "[Shutdown] Stopping Next.js frontend (PID: ${FRONTEND_PID})..."
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi
    if [ -n "$BACKEND_PID" ]; then
        echo "[Shutdown] Stopping FastAPI backend (PID: ${BACKEND_PID})..."
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    echo "[Shutdown] All services stopped. Exiting."
    exit 0
}

trap cleanup SIGINT SIGTERM

# 5. Launch FastAPI Backend with Uvicorn
echo "[Backend] Launching FastAPI ICT Scanner API and background orchestrator..."
uvicorn ict_scanner.api.main:app --host "${HOST}" --port "${BACKEND_PORT}" &
BACKEND_PID=$!
echo "[Backend] Started with PID: ${BACKEND_PID}"

# 6. Launch Next.js Frontend Dashboard
if [ -d "ict-scanner-dashboard" ]; then
    echo "[Frontend] Launching Next.js Control Room Dashboard..."
    (
        cd ict-scanner-dashboard
        if [ ! -d ".next" ]; then
            echo "[Frontend] Building Next.js application..."
            npm run build
        fi
        npm run start -- -H "${HOST}" -p "${FRONTEND_PORT}"
    ) &
    FRONTEND_PID=$!
    echo "[Frontend] Started with PID: ${FRONTEND_PID}"
else
    echo "[Frontend] Warning: 'ict-scanner-dashboard' directory not found. Running backend only."
fi

echo "=========================================================="
echo " ICT Scanner 24/7 is LIVE! Both services running in background. "
echo "=========================================================="

# 7. Supervise Both Processes
# If either process terminates, detect it and trigger shutdown
wait -n $BACKEND_PID $FRONTEND_PID 2>/dev/null || wait

EXIT_STATUS=$?
echo "[Process Manager] One of the services exited with status ${EXIT_STATUS}. Initiating shutdown..."
cleanup
