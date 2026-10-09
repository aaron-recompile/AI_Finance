#!/usr/bin/env python3
"""S6b cash-and-carry, one real round on the demo market (OKX Demo). x-simulated-trading
is hard-coded in okx_client.

Flow (= the flow Jarvis will later run; here you do it by hand):
  python carry_run.py check              # account mode / balances / contract spec / existing position -- read-only
  python carry_run.py set-mode           # switch account mode to 2 (spot and futures) -- changes a setting, asks for CONFIRM
  python carry_run.py open [--usdt 1000] # print plan -> type CONFIRM -> market-open both legs -> verify both filled, else close the filled one
  python carry_run.py status             # while holding: per-leg P&L, funding collected, current basis, next settle
  python carry_run.py close              # print plan -> type CONFIRM -> market-close both legs -> verify -> final ledger
State lives in carry_state.json (local, contains no key).
Export OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE first.
"""
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "okx"))
from okx_client import req

SPOT, SWAP = "BTC-USDT", "BTC-USDT-SWAP"
STATE = Path(__file__).parent / "carry_state.json"
MAX_USDT = 2000                                   # guardrail: notional cap per round


def call(method, path, body=None, private=True):
    # this script only fills on the demo market -> quotes, funding and contract spec all read demo too (demo=True)
    r = req(method, path, json.dumps(body) if body is not None else "", private=private, demo=True)
    if r.get("code") != "0":
        detail = "; ".join(f"sCode={d.get('sCode')} {d.get('sMsg')}" for d in r.get("data", []) if d.get("sCode"))
        raise SystemExit(f"X {method} {path.split('?')[0]} -> code={r.get('code')} {r.get('msg')} {detail}")
    return r["data"]


def confirm(what):
    print(f"\n!!  about to: {what}")
    if input("   type CONFIRM to execute, anything else cancels: ").strip() != "CONFIRM":
        raise SystemExit("Cancelled, nothing done.")


def book(inst):
    t = call("GET", f"/api/v5/market/ticker?instId={inst}", private=False)[0]
    return float(t["bidPx"]), float(t["askPx"])


def spec():
    d = call("GET", f"/api/v5/public/instruments?instType=SWAP&instId={SWAP}", private=False)[0]
    return float(d["ctVal"]), float(d["lotSz"]), float(d["minSz"])


def swap_pos():
    d = call("GET", f"/api/v5/account/positions?instType=SWAP&instId={SWAP}")
    return next((p for p in d if float(p.get("pos") or 0) != 0), None)


def wait_filled(inst, oid, tries=10):
    for _ in range(tries):
        o = call("GET", f"/api/v5/trade/order?instId={inst}&ordId={oid}")[0]
        if o["state"] in ("filled", "canceled", "mmp_canceled"):
            return o
        time.sleep(0.5)
    return o


def market(inst, side, sz, extra=None):
    body = {"instId": inst, "side": side, "ordType": "market", "sz": sz,
            "clOrdId": f"carry{int(time.time() * 1000)}"}
    body.update(extra or {})
    oid = call("POST", "/api/v5/trade/order", body)[0]["ordId"]
    return oid


MAX_SLIP = 0.001                                  # guardrail: at most 0.1% slip per leg, the rest doesn't fill


def capped(inst, side, sz, extra, tries=3):
    """Marketable limit IOC: willing to cross the book but slip at most MAX_SLIP; retry unfilled remainder
    at a refreshed price. Returns (filled_qty, avg_px, fee_usdt, remaining).
    The market open slipped 0.26% on a thin book once -- this is the fix."""
    left, filled, cost, fee = float(sz), 0.0, 0.0, 0.0
    for i in range(tries):
        bid, ask = book(inst)
        px = ask * (1 + MAX_SLIP) if side == "buy" else bid * (1 - MAX_SLIP)
        body = {"instId": inst, "side": side, "ordType": "ioc", "sz": f"{left:.8f}".rstrip("0").rstrip("."),
                "px": f"{px:.1f}", "clOrdId": f"carry{int(time.time() * 1000)}"}
        body.update(extra)
        oid = call("POST", "/api/v5/trade/order", body)[0]["ordId"]
        o = wait_filled(inst, oid)
        q = float(o["accFillSz"] or 0)
        if q:
            filled += q; cost += q * float(o["avgPx"]); fee += fee_usdt(o, float(o["avgPx"]))
        left = round(left - q, 8)
        print(f"    try {i + 1} {inst} {side} cap {px:,.1f} -> filled {q}, left {left}")
        if left <= 0:
            break
    return filled, (cost / filled if filled else 0), fee, left


def fee_usdt(o, px):
    f = float(o.get("fee") or 0)                  # negative = paid
    return f * px if o.get("feeCcy") == "BTC" else f


# ---------------------------------------------------------------- commands
def check(a):
    cfg = call("GET", "/api/v5/account/config")[0]
    lv = cfg["acctLv"]
    print(f"account mode acctLv={lv} {'OK can trade perps' if lv in ('2', '3', '4') else 'X spot-only mode, run set-mode first'}"
          f"   position mode {cfg['posMode']}   perm {cfg['perm']}")
    bal = {d["ccy"]: d for d in call("GET", "/api/v5/account/balance?ccy=USDT,BTC")[0]["details"]}
    for c in ("USDT", "BTC"):
        print(f"  {c:5} avail {bal.get(c, {}).get('availBal', '0')}")
    ctval, lot, mn = spec()
    print(f"contract spec {SWAP}: 1 contract = {ctval} BTC, min {mn} contracts, step {lot} contracts")
    p = swap_pos()
    print(f"existing perp position: {'none' if not p else p['pos'] + ' contracts'}   local state file: {'present (last round not closed?)' if STATE.exists() else 'none'}")


def set_mode(a):
    lv = call("GET", "/api/v5/account/config")[0]["acctLv"]
    if lv != "1":
        return print(f"already acctLv={lv}, no switch needed.")
    confirm("switch the demo account mode from 1 (spot) to 2 (spot and futures)")
    call("POST", "/api/v5/account/set-account-level", {"acctLv": "2"})
    print("OK switched. Run check again to confirm.")


def open_(a):
    if STATE.exists() or swap_pos():
        raise SystemExit("A round is already open (state file or perp position exists), run status / close first.")
    if a.usdt > MAX_USDT:
        raise SystemExit(f"guardrail: per-round cap is {MAX_USDT} USDT")
    if call("GET", "/api/v5/account/config")[0]["acctLv"] == "1":
        raise SystemExit("account is still in spot mode, run set-mode first")
    ctval, lot, mn = spec()
    sb, sa = book(SPOT)
    wb, wa = book(SWAP)
    contracts = round(int(a.usdt / sa / ctval / lot) * lot, 8)     # perp contracts, rounded down
    if contracts < mn:
        raise SystemExit(f"amount too small: below the minimum {mn} contracts")
    qty = round(contracts * ctval, 8)                              # buy the same amount of spot BTC
    fr = float(call("GET", f"/api/v5/public/funding-rate?instId={SWAP}", private=False)[0]["fundingRate"])
    print(f"plan: buy spot {qty} BTC (ask {sa:,.1f}) + short perp {contracts} contracts = {qty} BTC (bid {wb:,.1f})")
    print(f"      notional ~= {qty * sa:,.1f} USDT   basis {wb / sa - 1:+.3%}   current funding {fr:+.4%}/8h")
    confirm("market-open both legs (spot first, then perp)")

    t0 = time.time()
    o1 = market(SPOT, "buy", str(qty), {"tdMode": "cash", "tgtCcy": "base_ccy"})
    o2 = market(SWAP, "sell", str(contracts), {"tdMode": "cross"})
    f1, f2 = wait_filled(SPOT, o1), wait_filled(SWAP, o2)
    print(f"both legs accepted within {time.time() - t0:.2f}s")
    print(f"  spot {f1['state']}  filled {f1['accFillSz']} @ {f1.get('avgPx')}  fee {f1.get('fee')} {f1.get('feeCcy')}")
    print(f"  perp {f2['state']}  filled {f2['accFillSz']} contracts @ {f2.get('avgPx')}  fee {f2.get('fee')} {f2.get('feeCcy')}")

    if f1["state"] != "filled" or f2["state"] != "filled":
        # leg risk: one leg filled, the other didn't = naked position. Immediately close the filled leg
        print("X both legs did not fill -> rolling back the filled leg")
        if float(f1["accFillSz"] or 0) > 0:
            net = float(f1["accFillSz"]) + min(float(f1.get("fee") or 0), 0)
            market(SPOT, "sell", f"{net:.8f}", {"tdMode": "cash", "tgtCcy": "base_ccy"})
        if float(f2["accFillSz"] or 0) > 0:
            market(SWAP, "buy", f2["accFillSz"], {"tdMode": "cross", "reduceOnly": True})
        raise SystemExit("Rolled back. Check the check output to confirm it's clean.")

    spx, wpx = float(f1["avgPx"]), float(f2["avgPx"])
    spot_net = float(f1["accFillSz"]) + min(float(f1.get("fee") or 0), 0)   # fee deducted from the BTC received
    st = {"opened": time.time(), "spot_px": spx, "spot_qty": spot_net, "swap_px": wpx,
          "contracts": contracts, "ctval": ctval,
          "open_fees_usdt": fee_usdt(f1, spx) + fee_usdt(f2, wpx), "orders": [o1, o2]}
    STATE.write_text(json.dumps(st, indent=2))
    print(f"OK opened. actual basis {wpx / spx - 1:+.3%}, open fees {st['open_fees_usdt']:.4f} USDT")
    print(f"  spot net received {spot_net} BTC vs short perp {qty} BTC -> diff {qty - spot_net:.8f} (tiny exposure from the fee taken in coin)")


def pnl(st):
    sb, sa = book(SPOT)
    wb, wa = book(SWAP)
    spot_pnl = (sb - st["spot_px"]) * st["spot_qty"]                       # on close you sell spot at the bid
    swap_pnl = (st["swap_px"] - wa) * st["contracts"] * st["ctval"]       # on close you buy the short back at the ask
    bills = call("GET", "/api/v5/account/bills?instType=SWAP&type=8")      # type 8 = funding
    fund = sum(float(b["balChg"]) for b in bills
               if b.get("instId") == SWAP and int(b["ts"]) / 1000 >= st["opened"])
    return sb, sa, wb, wa, spot_pnl, swap_pnl, fund


def status(a):
    if not STATE.exists():
        raise SystemExit("no round currently open.")
    st = json.loads(STATE.read_text())
    sb, sa, wb, wa, sp, wp, fund = pnl(st)
    fr = call("GET", f"/api/v5/public/funding-rate?instId={SWAP}", private=False)[0]
    held = (time.time() - st["opened"]) / 3600
    print(f"held {held:.1f} h   next funding settle {datetime.fromtimestamp(int(fr['fundingTime']) / 1000):%m-%d %H:%M}"
          f" (rate {float(fr['fundingRate']):+.4%})")
    print(f"  spot leg {sp:+.4f}   perp leg {wp:+.4f}   -> after hedge, total {sp + wp:+.4f} USDT (~= basis change + spread)")
    print(f"  funding collected {fund:+.4f}   open fees {st['open_fees_usdt']:+.4f}")
    print(f"  if closed now (excl. close fees) ~= {sp + wp + fund + st['open_fees_usdt']:+.4f} USDT")
    p = swap_pos()
    if p:
        print(f"  exchange view: perp {p['pos']} contracts  liq price {p.get('liqPx') or '-'}  margin ratio {p.get('mgnRatio') or '-'}")


def close(a):
    if not STATE.exists():
        raise SystemExit("no round currently open.")
    st = json.loads(STATE.read_text())
    status(a)
    confirm(f"close both legs (limit IOC, per-leg slip cap {MAX_SLIP:.1%}): sell spot {st['spot_qty']:.8f} BTC + buy back perp {st['contracts']} contracts")
    sb, sa, wb, wa, sp, wp, fund = pnl(st)
    q1, spx, fee1, left1 = capped(SPOT, "sell", st["spot_qty"], {"tdMode": "cash"})
    q2, wpx, fee2, left2 = capped(SWAP, "buy", st["contracts"], {"tdMode": "cross", "reduceOnly": True})
    print(f"  spot sold {q1} @ {spx:,.2f}   perp bought back {q2} contracts @ {wpx:,.2f}")
    if left1 > 0 or left2 > 0:
        raise SystemExit(f"X not fully closed (spot left {left1}, perp left {left2} contracts) -- slip over the cap. State file kept, run close again later.")
    spot_leg = (spx - st["spot_px"]) * st["spot_qty"]
    swap_leg = (st["swap_px"] - wpx) * st["contracts"] * st["ctval"]
    fees = st["open_fees_usdt"] + fee1 + fee2
    total = spot_leg + swap_leg + fund + fees
    notional = st["spot_px"] * st["spot_qty"]
    hours = (time.time() - st["opened"]) / 3600
    print(f"\n=== final ledger for one carry round (held {hours:.1f} h, notional {notional:,.1f} USDT) ===")
    print(f"  spot leg {spot_leg:+.4f}   perp leg {swap_leg:+.4f}   (the two summed = the basis change left after hedging)")
    print(f"  funding {fund:+.4f}   four fees {fees:+.4f}")
    print(f"  total {total:+.4f} USDT = {total / notional:+.3%} of notional")
    done = STATE.with_name(f"carry_done_{int(time.time())}.json")
    st.update({"closed": time.time(), "result_usdt": total, "fund": fund, "fees": fees})
    done.write_text(json.dumps(st, indent=2)); STATE.unlink()
    print(f"  archived -> {done.name} (keep your own record; the exchange only keeps 3 months)")


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("check").set_defaults(fn=check)
sub.add_parser("set-mode").set_defaults(fn=set_mode)
s = sub.add_parser("open"); s.add_argument("--usdt", type=float, default=1000); s.set_defaults(fn=open_)
sub.add_parser("status").set_defaults(fn=status)
sub.add_parser("close").set_defaults(fn=close)
a = p.parse_args()
a.fn(a)
