# ---------------------------------------------------------------
# Hyperliquid read-only: OI / funding rate / order book (no wallet, no funds)
#   metaAndAssetCtxs -> per-perp funding / OI / markPx / volume
#   l2Book           -> order book (several levels each side)
# Run:  python hl_read.py
# ---------------------------------------------------------------
from hyperliquid.info import Info
from hyperliquid.utils import constants

COIN = "BTC"


def read(label, base_url):
    print(f"\n{'='*54}\n[{label}] {base_url}\n{'='*54}")
    info = Info(base_url, skip_ws=True)

    # 1) OI / funding / mark price -- pull all perps at once, pick out BTC
    meta, ctxs = info.meta_and_asset_ctxs()
    universe = meta["universe"]
    idx = next(i for i, a in enumerate(universe) if a["name"] == COIN)
    c = ctxs[idx]
    mark = float(c["markPx"])
    oracle = float(c["oraclePx"])
    funding_h = float(c["funding"])          # hourly funding rate
    oi_coin = float(c["openInterest"])       # open interest (in coin)
    vol_usd = float(c["dayNtlVlm"])          # 24h notional volume (USD)

    print(f"{COIN}  markPx={mark:,.1f}  oraclePx={oracle:,.1f}  premium={(mark/oracle-1)*100:+.3f}%")
    print(f"  funding (hourly): {funding_h*100:+.5f}%   -> annualized ~ {funding_h*24*365*100:+.1f}%")
    print(f"  open interest: {oi_coin:,.2f} {COIN}  ~= ${oi_coin*mark:,.0f}")
    print(f"  24h notional volume: ${vol_usd:,.0f}")

    # 2) top 5 of the book
    book = info.l2_snapshot(COIN)
    bids, asks = book["levels"][0], book["levels"][1]
    best_bid, best_ask = float(bids[0]["px"]), float(asks[0]["px"])
    mid = (best_bid + best_ask) / 2
    spread_bps = (best_ask - best_bid) / mid * 1e4
    print(f"  book: bid {best_bid:,.1f} / ask {best_ask:,.1f}  mid {mid:,.1f}  spread {spread_bps:.2f} bps")
    print("       bids                asks")
    for i in range(5):
        b = bids[i] if i < len(bids) else {"px": "-", "sz": "-"}
        a = asks[i] if i < len(asks) else {"px": "-", "sz": "-"}
        print(f"    {float(b['px']):>10,.1f} x {float(b['sz']):>8}   |   {float(a['px']):>10,.1f} x {float(a['sz']):>8}")


read("MAINNET (real liquidity, easier to interpret)", constants.MAINNET_API_URL)
read("TESTNET (your practice env)", constants.TESTNET_API_URL)
