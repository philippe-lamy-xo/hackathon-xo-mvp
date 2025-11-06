#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PIDFILE="$ROOT/server.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "No PID file; server may not be running"
  exit 0
fi

PID=$(cat "$PIDFILE")
if kill -0 "$PID" 2>/dev/null; then
  echo "Stopping server (PID $PID)"
  kill "$PID"
  sleep 0.4
  if kill -0 "$PID" 2>/dev/null; then
    echo "Server still running; forcing"
    kill -9 "$PID"
  fi
else
  echo "Process $PID not running"
fi
rm -f "$PIDFILE"
echo "Stopped"
