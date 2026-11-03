#!/bin/bash
# P1 Strategy Builder - Start Script
# Frontend: 3000, Backend: 8000

# Get absolute path of script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== P1 Strategy Builder ==="
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""

# 포트 충돌 시: node/python(uvicorn) 프로세스만 TERM으로 종료하고,
# 1초 뒤 남은 것만 KILL한다. 주문 처리 중인 다른 프로세스를 날리지 않도록 kill -9 즉시 사용 금지.
for port in 3000 8000; do
  for pid in $(lsof -ti:$port 2>/dev/null); do
    if ps -p "$pid" -o comm= 2>/dev/null | grep -qiE "node|python|uvicorn"; then
      kill "$pid" 2>/dev/null
    else
      echo "[경고] 포트 $port 점유 PID $pid 는 node/python이 아니라 남겨둡니다"
    fi
  done
done
sleep 1
for port in 3000 8000; do
  for pid in $(lsof -ti:$port 2>/dev/null); do
    if ps -p "$pid" -o comm= 2>/dev/null | grep -qiE "node|python|uvicorn"; then
      echo "[경고] 포트 $port PID $pid 가 아직 살아 있어 KILL합니다"
      kill -9 "$pid" 2>/dev/null
    fi
  done
done

# Start backend
cd "$SCRIPT_DIR"
echo "[Backend] Starting on port 8000..."
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 2

# Ensure frontend deps are installed
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
  echo "[Frontend] node_modules not found, running npm install..."
  (cd "$SCRIPT_DIR/frontend" && npm install) || { echo "npm install failed. Run: cd frontend && npm install"; exit 1; }
fi

# Start frontend
cd "$SCRIPT_DIR/frontend"
echo "[Frontend] Starting on port 3000..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

wait
