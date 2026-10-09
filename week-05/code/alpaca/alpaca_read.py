#!/usr/bin/env python3
"""Drill A1: read info (read-only). Compare with OKX's account state + public market data.
Usage: source alpaca_env.sh && python3 alpaca_read.py
"""
from alpaca_client import req, DATA

def show(title, st, d):
    print(f"\n=== {title} (HTTP {st}) ===")
    return d

a = show("account /v2/account", *req("GET", "/v2/account"))
for k in ["status", "cash", "equity", "buying_power", "shorting_enabled", "multiplier"]:
    print(f"  {k:20} {a.get(k)}")

c = show("market clock /v2/clock", *req("GET", "/v2/clock"))
print(f"  open now? {c['is_open']}  next open {c['next_open']}  next close {c['next_close']}")

p = show("positions /v2/positions", *req("GET", "/v2/positions"))
print(f"  {len(p)} total")
for x in p:
    print(f"  {x['symbol']:8} qty={x['qty']:>8} avg={x['avg_entry_price']:>10} uPnL={x['unrealized_pl']}")

o = show("open orders /v2/orders?status=open", *req("GET", "/v2/orders", params={"status": "open"}))
print(f"  {len(o)} total")

st, q = req("GET", "/v2/stocks/quotes/latest", params={"symbols": "GOOGL,GOOG,SPY,IVV,VOO"}, base=DATA)
show("latest stock quotes /v2/stocks/quotes/latest (free IEX feed)", st, q)
for s, x in (q or {}).get("quotes", {}).items():
    print(f"  {s:6} bid={x['bp']:>9} ask={x['ap']:>9}  time={x['t'][:19]}")

st, q = req("GET", "/v1beta3/crypto/us/latest/quotes", params={"symbols": "BTC/USD"}, base=DATA)
show("latest crypto quotes /v1beta3/crypto/us/latest/quotes", st, q)
for s, x in (q or {}).get("quotes", {}).items():
    print(f"  {s:8} bid={x['bp']:>10} ask={x['ap']:>10}  time={x['t'][:19]}")
print("\n(read-only: everything above is a GET.)")
