#!/data/data/com.termux/files/usr/bin/bash
# Launch the bridge for interactive use.
#   bridge.sh broker        -> start broker in background (detached)
#   bridge.sh cli           -> start the CLI client (connects to broker)
#   bridge.sh agent         -> start the Agent client (interactive)
#   bridge.sh all           -> broker + cli + agent, cleans up on exit
set -u
D="$(cd "$(dirname "$0")" && pwd)"
BROKER="$D/server.py"; CLI="$D/cli.py"; AGENT="$D/agent.py"; LOG="$D/broker.log"
PORT=8765

free_port() {
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${PORT}/tcp" 2>/dev/null
  fi
  for pid in $(pgrep -f "python3 $BROKER" 2>/dev/null); do
    kill "$pid" 2>/dev/null
  done
  sleep 1
}

start_broker() {
  free_port
  rm -f "$LOG"
  nohup setsid python3 -u "$BROKER" >"$LOG" 2>&1 </dev/null &
  for i in $(seq 1 20); do grep -q "listening" "$LOG" 2>/dev/null && break; sleep 0.25; done
  grep -q "listening" "$LOG" 2>/dev/null && echo "broker up" || { echo "broker failed:"; cat "$LOG"; return 1; }
}

stop_broker() { pkill -f "python3 $BROKER" 2>/dev/null; echo "broker stopped"; }

case "${1:-all}" in
  broker) start_broker ;;
  cli) python3 "$CLI" ;;
  agent) python3 "$AGENT" ;;
  all)
    start_broker || exit 1
    trap stop_broker EXIT
    python3 "$CLI" &
    CLI_PID=$!
    python3 "$AGENT"
    kill "$CLI_PID" 2>/dev/null
    ;;
  *) echo "usage: bridge.sh [broker|cli|agent|all]"; exit 1 ;;
esac
