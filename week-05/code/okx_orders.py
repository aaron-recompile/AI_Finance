#!/usr/bin/env python3
"""Drill 3 (Python): place / query / amend / cancel orders.
x-simulated-trading is hard-coded in okx_client, so this only touches the demo market.

Usage (export OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE first):
  python3 okx_orders.py place  [--side buy] [--type limit] [--px 10000] [--sz 0.0001]
  python3 okx_orders.py pending                     # current open orders
  python3 okx_orders.py get     ORDID               # one order
  python3 okx_orders.py amend   ORDID [--px P] [--sz S]
  python3 okx_orders.py cancel  ORDID
  python3 okx_orders.py cancel-all                  # cancel every open order on this market (kill-switch)
Common: --inst BTC-USDT (default)

Default order = limit buy 0.0001 BTC @ 10000: far from the market, won't fill,
just used to walk the full lifecycle once.
"""
import argparse, json, sys, time
from okx_client import req


def call(method, path, body=None):
    r = req(method, path, json.dumps(body) if body is not None else "")
    # Gotcha: the top-level code only reports the request as a whole. Batch/order endpoints
    # also carry a per-row sCode/sMsg.
    if r.get("code") != "0":
        print(f"X code={r.get('code')} msg={r.get('msg')}")
        for d in r.get("data", []):
            if d.get("sCode") not in (None, "0"):
                print(f"  -> sCode={d['sCode']} sMsg={d.get('sMsg')}")
        sys.exit(1)
    return r["data"]


def show(o):
    print(f"  ordId={o['ordId']} clOrdId={o.get('clOrdId') or '-'}")
    print(f"  {o['instId']} {o['side']} {o['ordType']} px={o.get('px') or 'market'} sz={o['sz']}"
          f"  filled={o.get('accFillSz')} avgPx={o.get('avgPx') or '-'}  state={o['state']}")


def place(a):
    body = {"instId": a.inst, "tdMode": "cash", "side": a.side, "ordType": a.type, "sz": a.sz,
            # clOrdId = your own order id: used to dedupe on network-timeout resends; a must for arb/agents
            "clOrdId": f"drill{int(time.time() * 1000)}"}
    if a.type == "limit":
        body["px"] = a.px
    else:
        # Gotcha: a spot market order's sz defaults to the QUOTE currency (buy = USDT amount).
        # Set tgtCcy so sz means the BASE currency (BTC) quantity.
        body["tgtCcy"] = "base_ccy"
    print("-> place", body)
    d = call("POST", "/api/v5/trade/order", body)[0]
    print(f"OK accepted ordId={d['ordId']} sCode={d['sCode']} (accepted != filled; use get to see state)")


def pending(a):
    rows = call("GET", f"/api/v5/trade/orders-pending?instType=SPOT&instId={a.inst}")
    print(f"open orders: {len(rows)}")
    for o in rows:
        show(o)


def get(a):
    show(call("GET", f"/api/v5/trade/order?instId={a.inst}&ordId={a.ordId}")[0])


def amend(a):
    body = {"instId": a.inst, "ordId": a.ordId}
    if a.px:
        body["newPx"] = a.px
    if a.sz:
        body["newSz"] = a.sz
    if len(body) == 2:
        sys.exit("amend needs at least --px or --sz")
    print("-> amend", body)
    d = call("POST", "/api/v5/trade/amend-order", body)[0]
    print(f"OK amend accepted ordId={d['ordId']}")


def cancel(a):
    d = call("POST", "/api/v5/trade/cancel-order", {"instId": a.inst, "ordId": a.ordId})[0]
    print(f"OK cancel accepted ordId={d['ordId']}")


def cancel_all(a):
    rows = call("GET", f"/api/v5/trade/orders-pending?instType=SPOT&instId={a.inst}")
    if not rows:
        print("no open orders")
        return
    body = [{"instId": o["instId"], "ordId": o["ordId"]} for o in rows][:20]  # batch cancel: max 20 at once
    for d in call("POST", "/api/v5/trade/cancel-batch-orders", body):
        print(f"  cancel {d['ordId']} -> sCode={d['sCode']} {d.get('sMsg') or ''}")


p = argparse.ArgumentParser()
p.add_argument("--inst", default="BTC-USDT")
sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("place"); s.set_defaults(fn=place)
s.add_argument("--side", default="buy", choices=["buy", "sell"])
s.add_argument("--type", default="limit", choices=["limit", "market"])
s.add_argument("--px", default="10000"); s.add_argument("--sz", default="0.0001")
sub.add_parser("pending").set_defaults(fn=pending)
for name, fn in [("get", get), ("cancel", cancel)]:
    s = sub.add_parser(name); s.add_argument("ordId"); s.set_defaults(fn=fn)
s = sub.add_parser("amend"); s.add_argument("ordId"); s.add_argument("--px"); s.add_argument("--sz")
s.set_defaults(fn=amend)
sub.add_parser("cancel-all").set_defaults(fn=cancel_all)

a = p.parse_args()
a.fn(a)
