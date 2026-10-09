# ---------------------------------------------------------------
# Two-leg funding arbitrage bot (Hyperliquid testnet): long spot POBTC + short BTC perp
#   Signing: API wallet (.agent.env, trade-only: can't withdraw/transfer); account: master
#   Runs one tick per hour: book the ledger -> check the rules -> close / alert / stay silent
#   Output contract (for an OpenClaw cron): print NO_REPLY when nothing's up; print a paragraph -> push Telegram
#   Setup:  copy .agent.env.example -> .agent.env and fill it in
# Run:  python hl_carry_bot.py status      show the ledger (always prints)
#       python hl_carry_bot.py open         open both legs (manual only, once)
#       python hl_carry_bot.py tick          called by the cron job
#       python hl_carry_bot.py close         manually close both legs
#   Kill-switch: create a file named STOP in this dir; the next tick closes and halts
# ---------------------------------------------------------------
import sys, json, time, csv, fcntl
from datetime import datetime
from pathlib import Path
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

BASE = Path(__file__).resolve().parent
STATE, LOG, STOP, LOCK = BASE / "carry_state.json", BASE / "carry_log.csv", BASE / "STOP", BASE / ".carry.lock"

# -- rules and hard limits (edit here = edit the risk controls) --
COIN, SPOT, SIZE, SPOT_DEC = "BTC", "@2072", 0.005, 5
CLOSE_BASIS_BELOW = 0.003      # basis shrinks below 0.3%: it narrowed, leave
ALERT_BASIS_ABOVE = 0.015      # basis widens above 1.5%: it's wide, just wait and alert
MAX_LOSS_USD = -10.0           # arb net below -10: circuit-break, force close
SPOT_EMPTY_ALERT_N = 3         # spot bid empty 3 times in a row: alert (the hedge leg may not sell)
MAX_DAYS = 7                   # hold at most 7 days, then close
ALERT_COOLDOWN_H = 6           # the same alert type at most once per 6 hours
DAILY_REPORT_HOUR = 9          # send one daily report at 9am local

env = dict(l.split("=", 1) for l in (BASE / ".agent.env").read_text().splitlines() if "=" in l and not l.startswith("#"))
MASTER = env["MASTER_ADDRESS"].strip()
info = Info(constants.TESTNET_API_URL, skip_ws=True)
ex = Exchange(Account.from_key(env["AGENT_PRIVATE_KEY"].strip()), constants.TESTNET_API_URL, account_address=MASTER)


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save(s):
    STATE.write_text(json.dumps(s, indent=1))


def market():
    meta, ctx = info.meta_and_asset_ctxs()
    c = ctx[[a["name"] for a in meta["universe"]].index(COIN)]
    for _ in range(4):                               # the POBTC maker bot blanks the book while re-quoting; read a few times
        book = info.l2_snapshot(SPOT)["levels"]
        if book[0] and book[1]:
            break
        time.sleep(3)
    bid = float(book[0][0]["px"]) if book[0] else None
    ask = float(book[1][0]["px"]) if book[1] else None
    return {"oracle": float(c["oraclePx"]), "mark": float(c["markPx"]), "funding": float(c["funding"]), "bid": bid, "ask": ask}


def perp_pos():
    for p in info.user_state(MASTER)["assetPositions"]:
        if p["position"]["coin"] == COIN:
            return p["position"]
    return None


def spot_qty():
    for b in info.spot_user_state(MASTER)["balances"]:
        if b["coin"] == "POBTC":
            return float(b["total"])
    return 0.0


def ledger(s, m):
    """Two-leg ledger, from the moment of open. Spot valued at the bid; when the bid is empty, use the oracle price."""
    spot_px = m["bid"] if m["bid"] else m["oracle"]
    spot_leg = s["spot_qty"] * (spot_px - s["spot_px"])
    perp_leg = -SIZE * (m["mark"] - s["perp_px"])
    fund = sum(float(x["delta"]["usdc"]) for x in info.post("/info", {"type": "userFunding", "user": MASTER, "startTime": s["t_open"]})
               if x["delta"]["coin"] == COIN)
    net = spot_leg + perp_leg + fund - s["fees_open"]
    return {"basis0": s["perp_px"] / s["spot_px"] - 1, "basis": m["mark"] / spot_px - 1, "spot_leg": spot_leg,
            "perp_leg": perp_leg, "funding": fund, "net": net, "spot_px_used": spot_px, "bid_empty": m["bid"] is None}


def summary(s, m, L, head):
    age_h = (time.time() * 1000 - s["t_open"]) / 3.6e6
    return (f"{head}\nheld {age_h:.1f}h . basis {L['basis0']*100:.3f}% -> {L['basis']*100:.3f}% . funding now {m['funding']*100:.4f}%/h\n"
            f"spot leg {L['spot_leg']:+.2f} . perp leg {L['perp_leg']:+.2f} . funding cum {L['funding']:+.2f} . open fee {-s['fees_open']:+.2f}\n"
            f"arb net {L['net']:+.2f} USDC" + ("\n! spot bid empty right now, valued at the oracle price" if L["bid_empty"] else ""))


def open_():
    s = load()
    if STOP.exists():
        print("a STOP file exists, opening is disabled (delete STOP to open)"); return
    if s.get("active") or perp_pos() or spot_qty() > 1e-4:
        print("already have a position or record, not opening again"); return
    m = market()
    if not m["ask"]:
        print("spot ask empty, can't buy, not opening"); return
    ex.update_leverage(1, COIN, is_cross=True)
    t = int(time.time() * 1000)
    r = ex.market_open(COIN, False, SIZE, None, 0.01)
    st = r["response"]["data"]["statuses"][0]
    if "filled" not in st:
        print("perp short open failed:", st); return
    perp_px = float(st["filled"]["avgPx"])
    r = ex.order(SPOT, True, SIZE, round(m["ask"] * 1.0003), {"limit": {"tif": "Ioc"}})
    st2 = r["response"]["data"]["statuses"][0]
    if "filled" not in st2:
        ex.market_close(COIN, None, None, 0.01)       # spot didn't fill -> pull the perp back immediately, no single leg
        print("spot didn't fill, rolled back the perp:", st2); return
    spot_px = float(st2["filled"]["avgPx"])
    time.sleep(2)
    fills = [f for f in info.user_fills(MASTER) if f["time"] >= t]
    fee_usd = sum(float(f["fee"]) * (spot_px if f["feeToken"] == "POBTC" else 1) for f in fills)
    s = {"active": True, "t_open": t, "perp_px": perp_px, "spot_px": spot_px, "spot_qty": spot_qty(),
         "fees_open": fee_usd, "spot_empty_n": 0, "alerts": {}, "last_daily": ""}
    save(s)
    print(f"opened both legs: short perp {SIZE} @ {perp_px}, long spot {s['spot_qty']} @ {spot_px}, entry basis {(perp_px/spot_px-1)*100:.3f}%, fees {fee_usd:.2f}")


def close(reason):
    s, m = load(), market()
    L = ledger(s, m)
    msgs = []
    if perp_pos():
        r = ex.market_close(COIN, None, None, 0.01)
        msgs.append("perp closed: " + json.dumps(r["response"]["data"]["statuses"][0], ensure_ascii=False))
    q = int(spot_qty() * 10**SPOT_DEC) / 10**SPOT_DEC
    sold = q < 10**-SPOT_DEC
    for _ in range(6):
        if sold: break
        bids = info.l2_snapshot(SPOT)["levels"][0]
        if bids:
            r = ex.order(SPOT, False, q, float(bids[0]["px"]), {"limit": {"tif": "Ioc"}})
            st = r["response"]["data"]["statuses"][0]
            if "filled" in st:
                msgs.append(f"spot sold {q} @ {st['filled']['avgPx']}"); sold = True; break
        time.sleep(10)
    if not sold:
        msgs.append("! can't sell spot (bid empty), perp is closed, spot still held, needs manual handling")
    s.update({"active": False, "closed_reason": reason, "t_close": int(time.time() * 1000), "final_net_est": L["net"]})
    save(s)
    print(summary(s, m, L, f"[ARB CLOSED] reason: {reason}") + "\n" + "\n".join(msgs))


def tick():
    s = load()
    if not s.get("active"):
        print("NO_REPLY"); return
    m = market()
    L = ledger(s, m)
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["time", "oracle", "mark", "spot_bid", "funding_h", "basis", "spot_leg", "perp_leg", "funding_cum", "net"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), m["oracle"], m["mark"], m["bid"], m["funding"],
                    round(L["basis"], 6), round(L["spot_leg"], 4), round(L["perp_leg"], 4), round(L["funding"], 4), round(L["net"], 4)])
    # 1) close rules (by priority)
    age_d = (time.time() * 1000 - s["t_open"]) / 8.64e7
    reason = None
    if STOP.exists():                          reason = "kill-switch (STOP file)"
    elif L["net"] < MAX_LOSS_USD:              reason = f"circuit break: arb net {L['net']:.2f} < {MAX_LOSS_USD}"
    elif m["funding"] < 0:                     reason = "funding turned negative (leave the moment it flips)"
    elif not L["bid_empty"] and L["basis"] < CLOSE_BASIS_BELOW: reason = f"basis shrank to {L['basis']*100:.3f}% (narrowed, leave)"
    elif age_d >= MAX_DAYS:                    reason = f"held {MAX_DAYS} days"
    if reason:
        close(reason); return
    # 2) alerts (with cooldown)
    s["spot_empty_n"] = s["spot_empty_n"] + 1 if L["bid_empty"] else 0
    alerts = []
    if L["basis"] > ALERT_BASIS_ABOVE:          alerts.append(("wide", f"basis widened to {L['basis']*100:.2f}% (wide, wait, don't close; a 1x position can hold)"))
    if s["spot_empty_n"] >= SPOT_EMPTY_ALERT_N: alerts.append(("empty", f"spot bid empty {s['spot_empty_n']} times in a row, the hedge leg may not sell"))
    now = time.time()
    fresh = [msg for k, msg in alerts if now - s["alerts"].get(k, 0) > ALERT_COOLDOWN_H * 3600]
    for k, _ in alerts:
        if now - s["alerts"].get(k, 0) > ALERT_COOLDOWN_H * 3600: s["alerts"][k] = now
    # 3) daily report
    today = datetime.now().strftime("%Y-%m-%d")
    daily = datetime.now().hour == DAILY_REPORT_HOUR and s["last_daily"] != today
    if daily: s["last_daily"] = today
    save(s)
    if fresh:
        print(summary(s, m, L, "[ARB ALERT] " + "; ".join(fresh)))
    elif daily:
        print(summary(s, m, L, "[ARB DAILY]"))
    else:
        print("NO_REPLY")


def status():
    s = load()
    if not s.get("active"):
        p = perp_pos()                              # no record != no position at the exchange: reconcile against the exchange
        print("bot has no active arb record", json.dumps({k: s.get(k) for k in ("closed_reason", "final_net_est")}, ensure_ascii=False))
        print(f"exchange check: BTC perp position {p['szi'] if p else 0}, spot POBTC {spot_qty()}"
              + (" ! exchange has a position but the bot has no record, reconcile manually" if p or spot_qty() > 1e-4 else " (account is flat)"))
        return
    m = market()
    print(summary(s, m, ledger(s, m), "[ARB STATUS]"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    with LOCK.open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)            # prevent two ticks running at once
        try:
            {"open": open_, "tick": tick, "close": lambda: close("manual close"), "status": status}[cmd]()
        except Exception as e:
            print(f"[ARB BOT ERROR] {cmd}: {type(e).__name__}: {e}")   # errors also push Telegram
            sys.exit(1)
