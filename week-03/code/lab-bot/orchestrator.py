"""orchestrator.py — the heartbeat that drives all bots + writes the dashboard state.

Every INTERVAL seconds: for each bot, scan(); if it's a hit and we're --live,
fire(). Accumulate P&L per strategy, write state.json (for dashboard.html) and
append fires to pnl.log. This is the local precursor to an OpenClaw Heartbeat.

    python orchestrator.py                 # DRY-RUN every 5s (safe, no tx)
    python orchestrator.py --interval 4
    python orchestrator.py --live          # LIVE: bots actually fire (needs PRIVATE_KEY + gas)
"""
import time, json, sys, os, importlib

BOTS = ["arb_bot", "liquidator_bot", "farm_bot", "dex_arb_bot", "rate_bot"]
HERE = os.path.dirname(__file__)
STATE = os.path.join(HERE, "state.json")
PNL = os.path.join(HERE, "pnl.log")


def _selected():
    # --only a,b   run just these ;  --skip a,b   run all but these
    bots = list(BOTS)
    if "--only" in sys.argv:
        bots = sys.argv[sys.argv.index("--only") + 1].split(",")
    if "--skip" in sys.argv:
        skip = sys.argv[sys.argv.index("--skip") + 1].split(",")
        bots = [b for b in bots if b not in skip]
    return bots


mods = [importlib.import_module(b) for b in _selected()]
acc = {m.NAME: {"pnl": 0.0, "fires": 0, "last_tx": None} for m in mods}


def tick(live, n):
    rows = []
    for m in mods:
        try:
            s = m.scan()
        except Exception as e:
            s = {"hit": False, "line": f"scan err: {e}"}
        a = acc[m.NAME]
        fired = False
        if s.get("hit") and live:
            try:
                r = m.fire(s)
                a["pnl"] += float(r.get("profit", 0) or 0)
                a["fires"] += 1
                a["last_tx"] = r.get("tx")
                fired = True
                with open(PNL, "a") as f:
                    f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "bot": m.NAME, **r}) + "\n")
            except Exception as e:
                s["line"] += f" | FIRE ERR: {e}"
        rows.append({"name": m.NAME, "hit": bool(s.get("hit")), "line": s.get("line", ""),
                     "pnl": round(a["pnl"], 2), "fires": a["fires"], "last_tx": a["last_tx"], "fired": fired})
    st = {"updated": time.strftime("%H:%M:%S"), "tick": n, "mode": "LIVE" if live else "DRY-RUN",
          "bots": rows, "total_pnl": round(sum(a["pnl"] for a in acc.values()), 2)}
    json.dump(st, open(STATE, "w"), indent=2)
    return st


def main():
    live = "--live" in sys.argv
    interval = int(sys.argv[sys.argv.index("--interval") + 1]) if "--interval" in sys.argv else 5
    print(f"orchestrator: {len(mods)} bots, heartbeat {interval}s  [{'LIVE' if live else 'DRY-RUN'}]  (Ctrl-C to stop)")
    n = 0
    while True:
        n += 1
        st = tick(live, n)
        hits = [b["name"] for b in st["bots"] if b["hit"]]
        print(f"[{st['updated']}] tick {n} | opportunities: {', '.join(hits) or 'none'} | total P&L {st['total_pnl']:+,.2f}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
