# ---------------------------------------------------------------
# Hyperliquid testnet: open a small short, watch funding land every hour
#   Signing: AGENT_PRIVATE_KEY from a local .agent.env (trade-only, can't withdraw); account: MASTER_ADDRESS
#   Ledger = funding received - fees +/- price PnL
#   Setup:   copy .agent.env.example -> .agent.env and fill it in
# Run:  python hl_funding.py open     set 1x cross -> market-short SIZE BTC
#       python hl_funding.py watch    snapshot: position, uPnL, funding received, net
#       python hl_funding.py close    market close (reduce-only)
#       python hl_funding.py ledger   full settlement ledger after close
# ---------------------------------------------------------------
import sys, time, json
from datetime import datetime
from pathlib import Path
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

HERE = Path(__file__).resolve().parent
env = dict(l.split("=", 1) for l in (HERE / ".agent.env").read_text().splitlines()
           if "=" in l and not l.startswith("#"))
agent = Account.from_key(env["AGENT_PRIVATE_KEY"].strip())
master = env["MASTER_ADDRESS"].strip()
info = Info(constants.TESTNET_API_URL, skip_ws=True)
exchange = Exchange(agent, constants.TESTNET_API_URL, account_address=master)

COIN, SIZE = "BTC", 0.005                      # ~$420 notional, 1x leverage
STATE = HERE / ".funding_run.json"             # records the open time, to filter this run's flow


def rate_now():
    meta, ctx = info.meta_and_asset_ctxs()
    c = ctx[[a["name"] for a in meta["universe"]].index(COIN)]
    return float(c["funding"]), float(c["oraclePx"]), float(c["markPx"])


def fills_since(t0):
    return [f for f in info.user_fills(master) if f["coin"] == COIN and f["time"] >= t0]


def fundings_since(t0):
    r = info.post("/info", {"type": "userFunding", "user": master, "startTime": t0})
    return [x for x in r if x["delta"]["coin"] == COIN]


def position():
    for p in info.user_state(master)["assetPositions"]:
        if p["position"]["coin"] == COIN:
            return p["position"]
    return None


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M:%S")


def open_():
    if position():
        print("already have a BTC position, close before opening"); return
    print("set BTC leverage 1x cross:", exchange.update_leverage(1, COIN, is_cross=True)["status"])
    f, oracle, mark = rate_now()
    print(f"before open: funding {f*100:.4f}%/h (annual {f*24*365*100:.0f}%), oracle {oracle}, mark {mark}")
    t0 = int(time.time() * 1000)
    r = exchange.market_open(COIN, False, SIZE, None, 0.01)   # False = sell = open short, 1% slippage cap
    print(json.dumps(r["response"]["data"]["statuses"], ensure_ascii=False))
    STATE.write_text(json.dumps({"t0": t0}))
    watch()


def watch():
    t0 = json.loads(STATE.read_text())["t0"]
    f, oracle, mark = rate_now()
    p = position()
    fills = fills_since(t0)
    fees = sum(float(x["fee"]) for x in fills)
    closed = sum(float(x["closedPnl"]) for x in fills)
    fund = fundings_since(t0)
    got = sum(float(x["delta"]["usdc"]) for x in fund)
    print(f"-- {datetime.now():%H:%M:%S}  current funding {f*100:.4f}%/h, oracle {oracle}, mark {mark}")
    if p:
        print(f"position {p['szi']} BTC  entry {p['entryPx']}  notional ${float(p['positionValue']):.2f}  "
              f"uPnL {float(p['unrealizedPnl']):+.4f}  liq px {p['liquidationPx']}")
        print(f"next hourly settle ~= {-float(p['szi']) * oracle * f:+.4f} USDC")
    else:
        print("no position")
    print("funding flow:")
    for x in fund:
        d = x["delta"]
        print(f"  {fmt(x['time'])}  rate {float(d['fundingRate'])*100:.4f}%  size {d['szi']}  received {float(d['usdc']):+.4f}")
    if not fund:
        print("  (no hourly settle yet)")
    upnl = float(p["unrealizedPnl"]) if p else 0.0
    print(f"ledger: funding {got:+.4f}  fees {-fees:+.4f}  realized price PnL {closed:+.4f}  uPnL {upnl:+.4f}"
          f"  -> net {got - fees + closed + upnl:+.4f} USDC")
    h = json.loads(STATE.read_text()).get("hedge")
    if h and p:
        hedge_view(h, p, fund)


def hedge_view(h, p, fund):
    # after a hedge leg is added, the two-leg carry ledger: only the change since the hedge moment
    bids = info.l2_snapshot(h["spot_coin"])["levels"][0]
    mark = float(p["positionValue"]) / abs(float(p["szi"]))
    if bids:
        bid = float(bids[0]["px"])                 # value spot at the bid you could sell into
    else:
        bid = float(info.meta_and_asset_ctxs()[1][[a["name"] for a in info.meta()["universe"]].index(COIN)]["oraclePx"])
        print("!! spot bid empty right now (can't sell), using oracle price to value")
    spot_leg = h["spot_qty"] * (bid - h["spot_px"])
    perp_leg = -abs(float(p["szi"])) * (mark - h["perp_mark"])
    fund_after = sum(float(x["delta"]["usdc"]) for x in fund if x["time"] >= h["t"])
    b0 = h["perp_mark"] / h["spot_px"] - 1
    b1 = mark / bid - 1
    net = spot_leg + perp_leg + fund_after - h["spot_fee_usd"]
    print(f"-- two-leg carry (hedged at {fmt(h['t'])}, entry basis {b0*100:.3f}%)")
    print(f"spot leg {h['spot_qty']} @ {h['spot_px']} -> bid {bid}: {spot_leg:+.4f}")
    print(f"perp leg {p['szi']} mark {h['perp_mark']} -> {mark:.1f}: {perp_leg:+.4f}")
    print(f"basis {b0*100:.3f}% -> {b1*100:.3f}% (two legs summed {spot_leg + perp_leg:+.4f} ~= basis change)")
    print(f"funding (after hedge) {fund_after:+.4f}  spot fee {-h['spot_fee_usd']:+.4f}  -> carry net {net:+.4f} USDC")


def close():
    p = position()
    if not p:
        print("no BTC position"); return
    r = exchange.market_close(COIN, None, None, 0.01)
    print(json.dumps(r["response"]["data"]["statuses"], ensure_ascii=False))
    time.sleep(2)
    watch()


def ledger():
    watch()


{"open": open_, "watch": watch, "close": close, "ledger": ledger}[sys.argv[1] if len(sys.argv) > 1 else "watch"]()
