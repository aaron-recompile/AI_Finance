#!/usr/bin/env python3
"""OKX cash-and-carry, Jarvis-side executor (demo market). Driven by the OpenClaw skill `okx-carry`.

Same logic as the by-hand carry_run.py; the only difference is how CONFIRM is done:
  by-hand:    input() waits for you to type CONFIRM
  Jarvis:     a one-time token -- plan first (prints a plan + a 6-digit token); after the boss
              replies CONFIRM in Telegram, Jarvis runs with the token. The token expires after
              10 minutes, is voided if price moved > 0.3%, and is deleted after one use.
              No token -> the executor refuses to place orders.

Commands:
  check                          read-only: account mode, balances, contract spec, whether a round is open
  plan-open [--usdt 1000]        print an open plan + token (no order)
  open --confirm TOKEN           execute the open
  status                         read-only: position, per-leg P&L, funding, whether an exit rule fired
  plan-close                     print a close plan + token (no order)
  close --confirm TOKEN          execute the close, print the final ledger and archive it

key: read into the process by itself from ~/.secrets/okx-demo.env -- never printed, Jarvis never touches it.
"""
import argparse, fcntl, json, os, secrets, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# okx_client.py ships in the repo's okx/ dir (../okx). Allow OKX_CLIENT_DIR to override.
for p in (HERE.parent / "okx", Path(os.environ.get("OKX_CLIENT_DIR", HERE.parent / "okx"))):
    if (p / "okx_client.py").exists():
        sys.path.insert(0, str(p)); break
KEYFILE = Path.home() / ".secrets" / "okx-demo.env"
if not os.environ.get("OKX_API_KEY") and KEYFILE.exists():
    for line in KEYFILE.read_text().splitlines():
        line = line.strip().removeprefix("export ").strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
from okx_client import req

SPOT, SWAP = "BTC-USDT", "BTC-USDT-SWAP"
STATE_DIR = HERE / "state"; STATE_DIR.mkdir(exist_ok=True)
STATE, PENDING, LOCK = STATE_DIR / "position.json", STATE_DIR / "pending.json", STATE_DIR / ".lock"
MAX_USDT = 2000          # notional cap per round
MAX_SLIP = 0.001         # per-leg slip cap 0.1%
TOKEN_TTL = 600          # token valid for 10 minutes
MAX_DRIFT = 0.003        # void if price moved > 0.3% between plan and execute
# exit rules (shared by status / gate)
EXIT_NEG_FUNDING_N = 3   # funding negative 3 periods in a row
EXIT_MAX_DAYS = 7        # held 7 days
EXIT_MAX_LOSS = -20.0    # unrealized loss over 20 USDT


def call(method, path, body=None, private=True):
    # only fills on the demo market -> quotes and funding also read demo (the demo market is separate)
    r = req(method, path, json.dumps(body) if body is not None else "", private=private, demo=True)
    if r.get("code") != "0":
        detail = "; ".join(f"sCode={d.get('sCode')} {d.get('sMsg')}" for d in r.get("data", []) if d.get("sCode"))
        raise SystemExit(f"X OKX rejected {path.split('?')[0]}: code={r.get('code')} {r.get('msg')} {detail}")
    return r["data"]


def book(inst):
    t = call("GET", f"/api/v5/market/ticker?instId={inst}", private=False)[0]
    return float(t["bidPx"]), float(t["askPx"])


def spec():
    d = call("GET", f"/api/v5/public/instruments?instType=SWAP&instId={SWAP}", private=False)[0]
    return float(d["ctVal"]), float(d["lotSz"]), float(d["minSz"])


def swap_pos():
    d = call("GET", f"/api/v5/account/positions?instType=SWAP&instId={SWAP}")
    return next((p for p in d if float(p.get("pos") or 0) != 0), None)


def recent_funding(n=3):
    d = call("GET", f"/api/v5/public/funding-rate-history?instId={SWAP}&limit={n}", private=False)
    return [float(x["realizedRate"] or x["fundingRate"]) for x in d]


def wait_filled(inst, oid, tries=10):
    for _ in range(tries):
        o = call("GET", f"/api/v5/trade/order?instId={inst}&ordId={oid}")[0]
        if o["state"] in ("filled", "canceled", "mmp_canceled"):
            return o
        time.sleep(0.5)
    return o


def fee_usdt(o, px):
    f = float(o.get("fee") or 0)
    return f * px if o.get("feeCcy") == "BTC" else f


def capped(inst, side, sz, extra, tries=3):
    """Limit IOC, at most MAX_SLIP per leg; refresh price and retry the unfilled remainder.
    Returns (filled_qty, avg_px, fee_usdt, remaining)."""
    left, filled, cost, fee = float(sz), 0.0, 0.0, 0.0
    for _ in range(tries):
        bid, ask = book(inst)
        px = ask * (1 + MAX_SLIP) if side == "buy" else bid * (1 - MAX_SLIP)
        body = {"instId": inst, "side": side, "ordType": "ioc", "sz": f"{left:.8f}".rstrip("0").rstrip("."),
                "px": f"{px:.1f}", "clOrdId": f"jcarry{int(time.time() * 1000)}"}
        body.update(extra)
        o = wait_filled(inst, call("POST", "/api/v5/trade/order", body)[0]["ordId"])
        q = float(o["accFillSz"] or 0)
        if q:
            filled += q; cost += q * float(o["avgPx"]); fee += fee_usdt(o, float(o["avgPx"]))
        left = round(left - q, 8)
        if left <= 0:
            break
    return filled, (cost / filled if filled else 0.0), fee, left


def new_pending(action, data):
    tok = f"{secrets.randbelow(10**6):06d}"
    PENDING.write_text(json.dumps({"action": action, "token": tok, "ts": time.time(), **data}))
    return tok


def take_pending(action, token):
    """Token check: exists, action matches, token matches, not expired. Deleted after one use."""
    if not PENDING.exists():
        raise SystemExit("X no plan awaiting confirmation. Run plan-open / plan-close first.")
    p = json.loads(PENDING.read_text())
    PENDING.unlink()                                          # win or lose, a token is single-use
    if p["action"] != action:
        raise SystemExit(f"X the pending plan is {p['action']}, not {action}. Make a new plan.")
    if token != p["token"]:
        raise SystemExit("X wrong token. Plan voided, make a new one.")
    if time.time() - p["ts"] > TOKEN_TTL:
        raise SystemExit("X plan older than 10 minutes, voided. Make a new one.")
    return p


# ---------------------------------------------------------------- read-only
def check(a):
    cfg = call("GET", "/api/v5/account/config")[0]
    bal = {d["ccy"]: d for d in call("GET", "/api/v5/account/balance?ccy=USDT,BTC")[0]["details"]}
    ctval, lot, mn = spec()
    p = swap_pos()
    print(f"account mode acctLv={cfg['acctLv']} ({'can trade perps' if cfg['acctLv'] in ('2', '3', '4') else 'spot-only, cannot trade perps'})  perm {cfg['perm']}")
    print(f"avail USDT {float(bal.get('USDT', {}).get('availBal', 0)):,.2f}   BTC {bal.get('BTC', {}).get('availBal', '0')}")
    print(f"contract: 1 = {ctval} BTC, min {mn} contracts")
    print(f"position: {'none' if not p and not STATE.exists() else 'a round is open'}   pending plan: {'yes' if PENDING.exists() else 'no'}")


def pnl(st):
    sb, sa = book(SPOT)
    wb, wa = book(SWAP)
    spot_pnl = (sb - st["spot_px"]) * st["spot_qty"]
    swap_pnl = (st["swap_px"] - wa) * st["contracts"] * st["ctval"]
    bills = call("GET", "/api/v5/account/bills?instType=SWAP&type=8")      # type 8 = funding
    fund = sum(float(b["balChg"]) for b in bills
               if b.get("instId") == SWAP and int(b["ts"]) / 1000 >= st["opened"])
    return spot_pnl, swap_pnl, fund


def exit_reasons(st, net):
    r = []
    fr = recent_funding(EXIT_NEG_FUNDING_N)
    if len(fr) == EXIT_NEG_FUNDING_N and all(x < 0 for x in fr):
        r.append(f"funding negative {EXIT_NEG_FUNDING_N} periods in a row ({', '.join(f'{x:+.4%}' for x in fr)})")
    if (time.time() - st["opened"]) / 86400 >= EXIT_MAX_DAYS:
        r.append(f"held {EXIT_MAX_DAYS} days")
    if net < EXIT_MAX_LOSS:
        r.append(f"unrealized loss {net:.2f} USDT over the cap {EXIT_MAX_LOSS}")
    return r


def status(a):
    if not STATE.exists():
        return print("no round currently open.")
    st = json.loads(STATE.read_text())
    sp, wp, fund = pnl(st)
    net = sp + wp + fund + st["open_fees_usdt"]
    hours = (time.time() - st["opened"]) / 3600
    print(f"held {hours:.1f} h, notional {st['spot_px'] * st['spot_qty']:,.0f} USDT")
    print(f"  two legs summed {sp + wp:+.2f} (spot {sp:+.2f} / perp {wp:+.2f})  funding {fund:+.2f}  open fees {st['open_fees_usdt']:+.2f}")
    print(f"  if closed now ~= {net:+.2f} USDT (excl. close fees)")
    rs = exit_reasons(st, net)
    print("  exit rules: " + ("; ".join(rs) + " -> suggest closing" if rs else "none fired, keep holding"))


# ---------------------------------------------------------------- open
def plan_open(a):
    if STATE.exists() or swap_pos():
        raise SystemExit("X a round is already open, not opening again.")
    if a.usdt > MAX_USDT:
        raise SystemExit(f"X over the per-round cap {MAX_USDT} USDT.")
    if call("GET", "/api/v5/account/config")[0]["acctLv"] == "1":
        raise SystemExit("X account is spot-only, cannot trade perps. Ask the boss to switch to 'spot and futures' mode in OKX demo settings.")
    ctval, lot, mn = spec()
    sb, sa = book(SPOT)
    wb, wa = book(SWAP)
    contracts = round(int(a.usdt / sa / ctval / lot) * lot, 8)
    if contracts < mn:
        raise SystemExit("X amount too small, below the minimum order size.")
    qty = round(contracts * ctval, 8)
    fr = recent_funding(3)
    tok = new_pending("open", {"usdt": a.usdt, "contracts": contracts, "qty": qty, "spot_ask": sa})
    print("[OKX demo - cash-and-carry - OPEN plan]")
    print(f"  buy spot {qty} BTC (~{qty * sa:,.0f} USDT) + short perp {contracts} contracts (= {qty} BTC)")
    print(f"  spot ask {sa:,.1f} / perp bid {wb:,.1f} -> basis {wb / sa - 1:+.3%}")
    print(f"  last 3 funding periods: {', '.join(f'{x:+.4%}' for x in fr)}"
          + ("  !! all negative, opening now means paying" if all(x < 0 for x in fr) else ""))
    print(f"  est. four fees ~{qty * sa * 0.0021:.2f} USDT; per-leg slip cap {MAX_SLIP:.1%}")
    print(f"  token {tok} (valid 10 minutes) -- execute after the boss replies CONFIRM")


def open_(a):
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)        # prevent two concurrent executions
        p = take_pending("open", a.confirm)
        if STATE.exists() or swap_pos():
            raise SystemExit("X a round is already open, not opening again.")
        sb, sa = book(SPOT)
        if abs(sa / p["spot_ask"] - 1) > MAX_DRIFT:
            raise SystemExit(f"X price moved {sa / p['spot_ask'] - 1:+.2%} since the plan, over {MAX_DRIFT:.1%}, voided. Make a new plan.")
        q1, spx, fee1, left1 = capped(SPOT, "buy", p["qty"], {"tdMode": "cash"})
        if q1 == 0:
            raise SystemExit("X bought no spot at all (slip over the cap), nothing opened.")
        # size the perp to the spot actually bought, so the two legs match
        ctval = spec()[0]
        contracts = round(int(round(q1 / ctval / 0.01, 6)) * 0.01, 8)   # round first to avoid float 118.999 -> 118
        q2, wpx, fee2, left2 = capped(SWAP, "sell", contracts, {"tdMode": "cross"})
        if q2 < contracts:
            # leg risk: the perp under-filled = naked spot long. Roll back: sell the spot, close the opened perp
            capped(SPOT, "sell", q1 + min(fee1 / spx, 0), {"tdMode": "cash"})
            if q2:
                capped(SWAP, "buy", q2, {"tdMode": "cross", "reduceOnly": True})
            raise SystemExit(f"X perp only opened {q2}/{contracts} contracts, rolled back both legs. Ask the boss to verify with check.")
        spot_net = q1 + fee1 / spx                              # fee1 is negative, taken from the BTC
        st = {"opened": time.time(), "spot_px": spx, "spot_qty": round(spot_net, 8), "swap_px": wpx,
              "contracts": contracts, "ctval": ctval, "open_fees_usdt": fee1 + fee2}
        STATE.write_text(json.dumps(st, indent=2))
        print("[OPENED]")
        print(f"  spot bought {q1} BTC @ {spx:,.1f}   perp short {q2} contracts @ {wpx:,.1f}   actual basis {wpx / spx - 1:+.3%}")
        print(f"  open fees {fee1 + fee2:.2f} USDT. From here it auto-checks every 8h and reminds the boss when it's time to close.")


# ---------------------------------------------------------------- close
def plan_close(a):
    if not STATE.exists():
        raise SystemExit("X no round currently open.")
    st = json.loads(STATE.read_text())
    sp, wp, fund = pnl(st)
    net = sp + wp + fund + st["open_fees_usdt"]
    tok = new_pending("close", {})
    print("[OKX demo - cash-and-carry - CLOSE plan]")
    print(f"  sell spot {st['spot_qty']} BTC + buy back perp {st['contracts']} contracts (limit IOC, per-leg slip cap {MAX_SLIP:.1%})")
    print(f"  now: two legs summed {sp + wp:+.2f}, funding {fund:+.2f}, open fees {st['open_fees_usdt']:+.2f} -> ~{net:+.2f} USDT (excl. close fees)")
    rs = exit_reasons(st, net)
    if rs:
        print("  exit rules fired: " + "; ".join(rs))
    print(f"  token {tok} (valid 10 minutes) -- execute after the boss replies CONFIRM")


def close(a):
    with open(LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        take_pending("close", a.confirm)
        st = json.loads(STATE.read_text())
        sp, wp, fund = pnl(st)
        q1, spx, fee1, left1 = capped(SPOT, "sell", st["spot_qty"], {"tdMode": "cash"})
        q2, wpx, fee2, left2 = capped(SWAP, "buy", st["contracts"], {"tdMode": "cross", "reduceOnly": True})
        if left1 > 0 or left2 > 0:
            st["spot_qty"], st["contracts"] = round(left1, 8), round(left2, 8)   # record only the remainder, close the rest next time
            STATE.write_text(json.dumps(st, indent=2))
            raise SystemExit(f"X not fully closed (spot left {left1} BTC, perp left {left2} contracts), slip over the cap. Run plan-close again later.")
        spot_leg = (spx - st["spot_px"]) * q1
        swap_leg = (st["swap_px"] - wpx) * q2 * st["ctval"]
        fees = st["open_fees_usdt"] + fee1 + fee2
        total = spot_leg + swap_leg + fund + fees
        notional = st["spot_px"] * q1
        hours = (time.time() - st["opened"]) / 3600
        st.update({"closed": time.time(), "result_usdt": total, "fund": fund, "fees": fees})
        (STATE_DIR / f"done_{int(time.time())}.json").write_text(json.dumps(st, indent=2))
        STATE.unlink()
        print(f"[CLOSED - final ledger] held {hours:.1f} h, notional {notional:,.0f} USDT")
        print(f"  two legs summed {spot_leg + swap_leg:+.2f} (spot {spot_leg:+.2f} / perp {swap_leg:+.2f})")
        print(f"  funding {fund:+.2f}   four fees {fees:+.2f}")
        print(f"  total {total:+.2f} USDT ({total / notional:+.3%} of notional)")


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
sub.add_parser("check").set_defaults(fn=check)
sub.add_parser("status").set_defaults(fn=status)
s = sub.add_parser("plan-open"); s.add_argument("--usdt", type=float, default=1000); s.set_defaults(fn=plan_open)
s = sub.add_parser("open"); s.add_argument("--confirm", required=True); s.set_defaults(fn=open_)
sub.add_parser("plan-close").set_defaults(fn=plan_close)
s = sub.add_parser("close"); s.add_argument("--confirm", required=True); s.set_defaults(fn=close)
if __name__ == "__main__":
    a = p.parse_args()
    a.fn(a)
