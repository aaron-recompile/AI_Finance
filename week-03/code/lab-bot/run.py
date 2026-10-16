"""run.py — heartbeat loop for ONE bot (orchestrator.py runs all five together).

    python run.py                     # arb_bot, DRY-RUN, every 5s
    python run.py liquidator_bot      # a specific bot
    python run.py rate_bot --interval 3 --live
"""
import sys, time, importlib

args = [a for a in sys.argv[1:] if not a.startswith("--")]
name = args[0] if args else "arb_bot"
mod = importlib.import_module(name)
interval = int(sys.argv[sys.argv.index("--interval") + 1]) if "--interval" in sys.argv else 5
live = "--live" in sys.argv

print(f"{mod.NAME} heartbeat every {interval}s  [{'LIVE' if live else 'DRY-RUN'}]  (Ctrl-C to stop)")
while True:
    try:
        s = mod.scan()
        print(f"[{time.strftime('%H:%M:%S')}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
        if s["hit"] and live:
            print("  fired:", mod.fire(s))
    except Exception as e:
        print("  err:", e)
    time.sleep(interval)
