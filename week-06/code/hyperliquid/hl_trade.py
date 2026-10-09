# ---------------------------------------------------------------
# Hyperliquid testnet: check account + safe order demo (rest an order far from the book -> cancel immediately, never fills)
#   Goal: walk the place/cancel path by hand, see the response shapes, zero fills, zero loss
#   Setup: put your TESTNET key in a local .env (see .env.example):  PRIVATE_KEY=0x...
# Run:  python hl_trade.py
# ---------------------------------------------------------------
from pathlib import Path
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

HERE = Path(__file__).resolve().parent
pk = next(l.split("=", 1)[1].strip() for l in (HERE / ".env").read_text().splitlines() if l.startswith("PRIVATE_KEY="))
wallet = Account.from_key(pk)
addr = wallet.address
print("wallet:", addr)

info = Info(constants.TESTNET_API_URL, skip_ws=True)

# -- 1) check account state --------------------------------
state = info.user_state(addr)
ms = state.get("marginSummary", {})
acct_value = float(ms.get("accountValue", 0))
withdrawable = float(state.get("withdrawable", 0))
print(f"\naccount value: ${acct_value:,.2f}   withdrawable: ${withdrawable:,.2f}")
positions = state.get("assetPositions", [])
if positions:
    print("positions:")
    for p in positions:
        pos = p["position"]
        print(f"  {pos['coin']}  size {pos['szi']}  entry {pos.get('entryPx')}  uPnL {pos.get('unrealizedPnl')}")
else:
    print("positions: none")

# -- 2) stop if empty, point to the faucet -----------------
if acct_value <= 0:
    print("\n!! testnet account has no USDC. Get testnet funds on Hyperliquid testnet first, then run this order demo.")
    raise SystemExit(0)

# -- 3) safe order: BTC limit buy @ $30,000 (far below market, won't fill) -> cancel immediately --
exchange = Exchange(wallet, constants.TESTNET_API_URL)
print("\n(1) place: BTC limit buy 0.001 @ $30,000 (GTC, far from the book, won't fill)...")
resp = exchange.order("BTC", True, 0.001, 30000, {"limit": {"tif": "Gtc"}})
print("   order response:", resp)

# pull the oid from the response
try:
    status = resp["response"]["data"]["statuses"][0]
    oid = status.get("resting", {}).get("oid") or status.get("filled", {}).get("oid")
    print("   -> oid:", oid)
    if oid:
        print("(2) cancel...")
        cancel_resp = exchange.cancel("BTC", oid)
        print("   cancel response:", cancel_resp)
except Exception as e:
    print("   parse/cancel error:", e, "| see the raw response above; cancel in the testnet UI if needed")
