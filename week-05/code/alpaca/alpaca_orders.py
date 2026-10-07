#!/usr/bin/env python3
"""Drill A2: place / query / amend / cancel orders (Alpaca PAPER). Compare with okx_orders.py.

Usage (source alpaca_env.sh first):
  python3 alpaca_orders.py place  [--sym BTC/USD] [--side buy] [--type limit] [--px 10000] [--qty 0.0001] [--tif gtc]
  python3 alpaca_orders.py pending
  python3 alpaca_orders.py get     ORDER_ID
  python3 alpaca_orders.py amend   ORDER_ID [--px P] [--qty Q]
  python3 alpaca_orders.py cancel  ORDER_ID
  python3 alpaca_orders.py cancel-all

Default order = BTC/USD limit buy 0.002 @ 10000 (= $20): far from the market, won't fill.
  Gotcha: a crypto order has a $10 minimum, computed as (limit price x qty) (0.0001@10000=$1 -> HTTP 403 "cost basis must be >= 10"). Crypto is 24/7, so you can practice after hours too.
Stock example: --sym GOOGL --qty 1 --px 100 --tif day (an order placed while closed queues to the next open)

Differences from OKX (all noted at the matching spot in the code):
  - time_in_force is required: stocks day/gtc/ioc/fok/opg/cls; crypto only accepts gtc/ioc
  - amend = PATCH, which creates a NEW order id and leaves the old one "replaced" (OKX amend keeps the same ordId)
  - success/failure is the HTTP status code: cancel ok 204, can't cancel 422 (OKX is 200 + sCode 51400)
"""
import argparse, sys, time
from alpaca_client import req


def call(method, path, body=None, params=None, ok=(200, 204, 207)):
    st, d = req(method, path, body, params)
    if st not in ok:
        print(f"X HTTP {st} {d.get('message') if isinstance(d, dict) else d}")
        sys.exit(1)
    return st, d


def show(o):
    print(f"  id={o['id']}  client_order_id={o.get('client_order_id')}")
    print(f"  {o['symbol']} {o['side']} {o['type']} px={o.get('limit_price') or 'market'} qty={o.get('qty')}"
          f" tif={o['time_in_force']}  filled={o.get('filled_qty')} avg={o.get('filled_avg_price') or '-'}"
          f"  status={o['status']}")
    if o.get("replaced_by"):
        print(f"  -> replaced by a new order replaced_by={o['replaced_by']}")


def place(a):
    body = {"symbol": a.sym, "side": a.side, "type": a.type, "qty": a.qty, "time_in_force": a.tif,
            # like OKX clOrdId: used to dedupe on a timeout resend
            "client_order_id": f"drill{int(time.time() * 1000)}"}
    if a.type == "limit":
        body["limit_price"] = a.px
    print("-> place", body)
    _, o = call("POST", "/v2/orders", body)
    print("OK accepted (accepted != filled; use get to see state)")
    show(o)


def pending(a):
    _, rows = call("GET", "/v2/orders", params={"status": "open"})
    print(f"open orders: {len(rows)}")
    for o in rows:
        show(o)


def get(a):
    show(call("GET", f"/v2/orders/{a.oid}")[1])


def amend(a):
    body = {}
    if a.px:
        body["limit_price"] = a.px
    if a.qty:
        body["qty"] = a.qty
    if not body:
        sys.exit("amend needs at least --px or --qty")
    # Gotcha: a PATCH without client_order_id gets a random UUID, breaking your own id chain.
    # Fix: reuse the old id + "-r<n>", so you can trace it back after several amends.
    _, old = call("GET", f"/v2/orders/{a.oid}")
    base, _, n = old["client_order_id"].partition("-r")
    body["client_order_id"] = f"{base}-r{int(n) + 1 if n.isdigit() else 1}"
    print("-> amend PATCH", body)
    _, o = call("PATCH", f"/v2/orders/{a.oid}", body)
    print("OK amend accepted -- note: this is a NEW order, the id changed")
    show(o)


def cancel(a):
    st, _ = call("DELETE", f"/v2/orders/{a.oid}")
    print(f"OK cancel accepted (HTTP {st}) -- get it again to confirm canceled")


def cancel_all(a):
    _, rows = call("DELETE", "/v2/orders")
    print(f"cancel requests: {len(rows or [])}")
    for r in rows or []:
        print(f"  {r['id']} -> HTTP {r['status']}")


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
s = sub.add_parser("place"); s.set_defaults(fn=place)
s.add_argument("--sym", default="BTC/USD")
s.add_argument("--side", default="buy", choices=["buy", "sell"])
s.add_argument("--type", default="limit", choices=["limit", "market"])
s.add_argument("--px", default="10000"); s.add_argument("--qty", default="0.002")
s.add_argument("--tif", default="gtc", choices=["day", "gtc", "ioc", "fok", "opg", "cls"])
sub.add_parser("pending").set_defaults(fn=pending)
for name, fn in [("get", get), ("cancel", cancel)]:
    s = sub.add_parser(name); s.add_argument("oid"); s.set_defaults(fn=fn)
s = sub.add_parser("amend"); s.add_argument("oid"); s.add_argument("--px"); s.add_argument("--qty")
s.set_defaults(fn=amend)
sub.add_parser("cancel-all").set_defaults(fn=cancel_all)

a = p.parse_args()
a.fn(a)
