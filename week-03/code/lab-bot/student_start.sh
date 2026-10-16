#!/usr/bin/env bash
# student_start.sh — run YOUR OWN bot dashboard (read-only: no wallet, no gas, no risk).
#
# Your five bots scan the shared testnet every few seconds. The moment the instructor
# skews the market, a row on YOUR dashboard lights up GREEN — your own program spotted
# the opportunity, independently, by reading the public chain.
#
#   ./student_start.sh          # start  ->  http://localhost:8010/dashboard.html
#   ./student_start.sh stop     # stop
#
# First time only, if it complains web3 is missing:
#   python3 -m pip install web3
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8010
cd "$DIR"

stop() {
  pkill -f "orchestrator.py" 2>/dev/null || true
  lsof -ti:$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
  echo "stopped (port $PORT + orchestrator)."
}
if [ "$1" = "stop" ]; then stop; exit 0; fi

# pick a python that can import web3
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import web3" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "!! Python can't import web3 yet. Install it once, then re-run:"
  echo "       python3 -m pip install web3"
  exit 1
fi

stop  # clean slate so re-running is safe

# 1) a tiny web server so dashboard.html can fetch state.json (file:// can't)
nohup "$PY" -m http.server $PORT >/tmp/student_httpd.log 2>&1 &
# 2) your bots — DRY-RUN (never sends a transaction) + a gentle 12s heartbeat (kind to the public RPC)
nohup "$PY" orchestrator.py --interval 12 >/tmp/student_orch.log 2>&1 &

sleep 1
echo ""
echo "  ✅  Your bot dashboard is live — DRY-RUN, read-only, no wallet, no gas:"
echo ""
echo "         http://localhost:$PORT/dashboard.html"
echo ""
echo "  Watch it while the instructor skews the market. A GREEN row = your own bot"
echo "  found the opportunity. It's only watching — it never fires a trade."
echo "  Stop when done:   ./student_start.sh stop"
echo ""
