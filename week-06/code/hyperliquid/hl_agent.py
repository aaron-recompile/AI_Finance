# ---------------------------------------------------------------
# Hyperliquid testnet: use an API wallet (agent key) to place/cancel for the master account
#   Signing: AGENT_PRIVATE_KEY from a local .agent.env (trade-only: can trade, cannot withdraw)
#   Account: MASTER_ADDRESS (your main account) -> orders show up under its "open orders"
#   Safety:  only post-only (ALO) buys at half the mid price, so they never fill
#   Setup:   copy .agent.env.example -> .agent.env and fill it in
# Run:  python hl_agent.py status   balance + open orders
#       python hl_agent.py place    rest a BTC buy far from the book
#       python hl_agent.py cancel    cancel all BTC open orders on the master account
# ---------------------------------------------------------------
import sys, json
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
exchange = Exchange(agent, constants.TESTNET_API_URL, account_address=master)   # agent signs, booked under master

COIN, SIZE = "BTC", 0.0003          # ~$12 notional, clears the $10 minimum


def status():
    ms = info.user_state(master)["marginSummary"]
    print(f"master {master[:6]}...  account value {ms['accountValue']} USDC  signing agent {agent.address[:6]}...")
    oo = info.open_orders(master)
    print("open orders:", oo if oo else "none")


def place():
    mid = float(info.all_mids()[COIN])
    px = float(f"{mid * 0.5:.5g}")    # 5 significant figures, satisfies price-precision rules
    print(f"{COIN} mid {mid}, resting post-only buy {SIZE} @ {px} (half the mid, won't fill)")
    r = exchange.order(COIN, True, SIZE, px, {"limit": {"tif": "Alo"}})
    print(json.dumps(r, indent=2, ensure_ascii=False))


def cancel():
    oo = [o for o in info.open_orders(master) if o["coin"] == COIN]
    if not oo:
        print("no BTC open orders"); return
    for o in oo:
        r = exchange.cancel(COIN, o["oid"])
        print(f"cancel oid {o['oid']}:", json.dumps(r, ensure_ascii=False))


{"status": status, "place": place, "cancel": cancel}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
