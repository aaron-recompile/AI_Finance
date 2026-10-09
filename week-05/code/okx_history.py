#!/usr/bin/env python3
"""Drill 2b: historical lookback (read-only). Orders -> fills -> bills, three layers of the
same event. GET only, places no orders.
Usage: export OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE && python3 okx_history.py
       optional: INST=BTC-USDT (default)
"""
import datetime as dt, os
from okx_client import req

INST = os.environ.get("INST", "BTC-USDT")
CCY = INST.split("-")[0]


def t(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000).strftime("%Y-%m-%d %H:%M:%S") if ms else "-"


def fetch(title, path):
    print(f"=== {title} ===")
    r = req("GET", path)
    if r.get("code") != "0":
        print("  error:", r.get("code"), r.get("msg"))
        return []
    print(f"  {len(r['data'])} rows")
    return r["data"]


for x in fetch(f"(1) orders - last 3 months orders-history-archive ({INST})",
               f"/api/v5/trade/orders-history-archive?instType=SPOT&instId={INST}&limit=100"):
    print(f"  {t(x['cTime'])} {x['side']:4} {x['ordType']:7} px={x.get('px') or 'market':>10} "
          f"sz={x['sz']:>8} filled={x['accFillSz']:>8} avgPx={x.get('avgPx') or '-':>10} state={x['state']}")
print()
for x in fetch(f"(2) fills - last 3 months fills-history ({INST})",
               f"/api/v5/trade/fills-history?instType=SPOT&instId={INST}&limit=100"):
    role = "maker" if x.get("execType") == "M" else "taker"
    print(f"  {t(x['ts'])} {x['side']:4} px={x['fillPx']:>10} sz={x['fillSz']:>10} "
          f"fee={x['fee']} {x['feeCcy']} {role} ordId={x['ordId']}")
print()
for x in fetch(f"(3) account bills - last 3 months bills-archive ({CCY})",
               f"/api/v5/account/bills-archive?ccy={CCY}&limit=100"):
    print(f"  {t(x['ts'])} {x['ccy']:5} chg={x['balChg']:>14} bal={x['bal']:>14} "
          f"type={x['type']} subType={x['subType']}")
print("\n(read-only: everything above is a GET.)")
