#!/usr/bin/env python3
"""OKX carry fast-layer: pure rule check, no AI call, no orders. Run by an OpenClaw cron job
5 minutes after each funding settlement.

no position / no rule fired -> print NO_REPLY (OpenClaw then sends no Telegram)
rule fired -> print the alert (OpenClaw sends it to the boss's Telegram); wait for the boss to
say "close" before running plan-close -> CONFIRM.
Same reason alerts at most once per 8 hours.
"""
import io, json, sys, time
from contextlib import redirect_stdout
import carry_agent as ca

COOLDOWN = 8 * 3600
mark = ca.STATE_DIR / "gate_last_alert.json"

try:
    if not ca.STATE.exists():
        print("NO_REPLY"); sys.exit()
    st = json.loads(ca.STATE.read_text())
    sp, wp, fund = ca.pnl(st)
    net = sp + wp + fund + st["open_fees_usdt"]
    reasons = ca.exit_reasons(st, net)
    if not reasons:
        print("NO_REPLY"); sys.exit()
    key = "|".join(r.split("(")[0].strip() for r in reasons)
    last = json.loads(mark.read_text()) if mark.exists() else {}
    if last.get("key") == key and time.time() - last.get("ts", 0) < COOLDOWN:
        print("NO_REPLY"); sys.exit()
    mark.write_text(json.dumps({"key": key, "ts": time.time()}))
    print("[OKX carry alert] exit rule fired: " + "; ".join(reasons))
    print(f"now ~{net:+.2f} USDT (two legs {sp + wp:+.2f} / funding {fund:+.2f} / open fees {st['open_fees_usdt']:+.2f})")
    print("Reply 'close' to close; Jarvis will send a close plan first, then you reply CONFIRM.")
except SystemExit as e:
    if isinstance(e.code, str):              # the executor's error (e.g. OKX rejected) should also go out
        print(f"[OKX carry check error] {e.code}")
    else:
        raise
except Exception as e:                       # a failure in the check itself should reach the boss too
    print(f"[OKX carry check error] {type(e).__name__}: {e}")
