#!/data/data/com.termux/files/usr/bin/bash
# Self-terminating smoke test: starts broker, runs smoke, kills broker.
# Hard-capped by `timeout` so a hung client can NEVER wedge the SSH channel.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
BROKER="$D/server.py"
SMOKE="$D/_smoke.py"
LOG="$D/broker.log"
PORT=8765

# Bail if something is already on the port
if pgrep -f "python3 $BROKER" >/dev/null; then
  echo "broker already running; kill it first: pkill -f server.py"
  exit 1
fi

rm -f "$LOG"
# Start broker fully detached (nohup + setsid + disown), redirect all fds
nohup setsid python3 -u "$BROKER" >"$LOG" 2>&1 </dev/null &
BPID=$!
# Give it a moment, verify it came up
for i in $(seq 1 20); do
  if grep -q "listening" "$LOG" 2>/dev/null; then break; fi
  sleep 0.25
done
if ! grep -q "listening" "$LOG" 2>/dev/null; then
  echo "broker failed to start:"; cat "$LOG"
  kill "$BPID" 2>/dev/null
  exit 1
fi
echo "broker up (pid $BPID)"

# Run smoke, hard-capped at 15s (so SSH channel always closes)
timeout 15 python3 "$SMOKE"
RC=$?
echo "smoke exit: $RC"

# ALWAYS clean up the broker
kill "$BPID" 2>/dev/null
pkill -f "python3 $BROKER" 2>/dev/null
sleep 0.5
echo "broker stopped; channel clean"
