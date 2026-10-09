from hyperliquid.info import Info
from hyperliquid.utils import constants

# Read-only on MAINNET. skip_ws=True = REST only, no websocket.
# Reads need no wallet / private key.
info = Info(constants.MAINNET_API_URL, skip_ws=True)

# 1) mid prices for every market
mids = info.all_mids()
print("BTC mid:", mids.get("BTC"))
print("ETH mid:", mids.get("ETH"))
print("currently", len(mids), "markets quoting")

# 2) BTC on-chain order book (L2 snapshot) -- this is the "on-chain CLOB"
book = info.l2_snapshot("BTC")
bids, asks = book["levels"]
print("\nBTC order book (top 5 each side):")
print(f"{'bid px':>14} {'sz':>10}   |   {'ask px':>14} {'sz':>10}")
for i in range(5):
    b, a = bids[i], asks[i]
    print(f"{b['px']:>14} {b['sz']:>10}   |   {a['px']:>14} {a['sz']:>10}")

best_bid, best_ask = float(bids[0]["px"]), float(asks[0]["px"])
spread = best_ask - best_bid
print(f"\nbest bid {best_bid} / best ask {best_ask}")
print(f"spread: {spread:.2f}  ({spread/best_bid*10000:.2f} bps)")
