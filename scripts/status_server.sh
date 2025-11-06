#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PIDFILE="$ROOT/server.pid"
LOG="$ROOT/server.log"

if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Server running (PID $PID)"
    echo "-- last 20 lines of log --"
    tail -n 20 "$LOG" || true
    exit 0
  else
    echo "PID file exists but process $PID not running"
    exit 1
  fi
else
  echo "Server not running (no $PIDFILE)"
  exit 1
fi
