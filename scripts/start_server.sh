#!/usr/bin/env bash
# Start the demo server if not already running.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PIDFILE="$ROOT/server.pid"
LOG="$ROOT/server.log"

# If pidfile exists and process is alive, exit.
if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Server already running (PID $PID)"
    exit 0
  else
    echo "Removing stale PID file"
    rm -f "$PIDFILE"
  fi
fi

# Try to detect an existing python process running scripts/server.py and adopt it
EXISTING_PID=$(ps -eo pid,cmd | grep '[s]cripts/server.py' | awk '{print $1}' | head -n 1 || true)
if [ -n "$EXISTING_PID" ]; then
  echo "Adopting existing server process PID $EXISTING_PID"
  echo "$EXISTING_PID" > "$PIDFILE"
  echo "Logs -> $LOG"
  exit 0
fi

echo "Starting server... logs -> $LOG"
nohup python3 "$ROOT/scripts/server.py" >"$LOG" 2>&1 &
NEWPID=$!
echo "$NEWPID" > "$PIDFILE"
echo "Started (PID $NEWPID)"
