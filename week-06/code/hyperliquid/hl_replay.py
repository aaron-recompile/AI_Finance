# ---------------------------------------------------------------
# Minimal replay engine: put the three pieces together to show "naive backtest vs honest replay"
#   price = candles . fills = mid + slippage . carry = settle funding each hour
#   Same market exposure, compare "buy and hold (2 fills)" vs "flip short/long every hour (48 fills)"
#   -> see how overtrading feeds profit to slippage (the quant version of "backtests flatter, live hits back")
# Run:  python hl_replay.py [COIN]   default BTC
# ---------------------------------------------------------------
import sys, time
from hyperliquid.info import Info
from hyperliquid.utils import constants

COIN = sys.argv[1] if len(sys.argv) > 1 else "BTC"
NOTIONAL = 1_000_000        # notional per open (USD)
NOW = int(time.time() * 1000); DAY = 24 * 3600 * 1000
info = Info(constants.MAINNET_API_URL, skip_ws=True)

candles = info.candles_snapshot(COIN, "1h", NOW - DAY, NOW)
fh = info.funding_history(COIN, NOW - DAY, NOW)
entry, exit_ = float(candles[0]["o"]), float(candles[-1]["c"])
hours = len(candles)

# estimate one-side slippage (bps) from the current book -- historical book isn't available, so approximate with the current book (flagged honestly)
def slip_bps(usd):
    b = info.l2_snapshot(COIN); bids, asks = b["levels"][0], b["levels"][1]
    mid = (float(bids[0]["px"]) + float(asks[0]["px"])) / 2
    rem, cost, sz = usd, 0.0, 0.0
    for lvl in asks:
        px, s = float(lvl["px"]), float(lvl["sz"]); take = min(rem, px * s)
        sz += take / px; cost += take; rem -= take
        if rem <= 0: break
    return (cost / sz - mid) / mid * 1e4 if sz else 0.0

sbps = slip_bps(NOTIONAL)
slip_per_fill = NOTIONAL * sbps / 1e4                 # slippage cost per fill (USD)
funding_sum = sum(float(x["fundingRate"]) for x in fh)  # held throughout; longs pay positive funding
funding_cost = funding_sum * NOTIONAL

gross = (exit_ / entry - 1) * NOTIONAL                 # naive: price move only, zero cost

print(f"coin {COIN} | notional ${NOTIONAL:,} | {hours} hours | in {entry:,.1f} -> out {exit_:,.1f} ({(exit_/entry-1)*100:+.2f}%)")
print(f"one-side slip ~= {sbps:.2f} bps = ${slip_per_fill:,.0f}/fill | whole-run funding = {funding_sum*100:+.4f}% = ${funding_cost:,.0f}")
print()
print(f"{'strategy':<26}{'naive PnL':>12}{'slip cost':>12}{'funding':>10}{'honest PnL':>12}")
for name, fills in [("buy & hold (2 fills)", 2), ("flip every hour (48)", hours * 2)]:
    slip_cost = fills * slip_per_fill
    honest = gross - slip_cost - funding_cost
    print(f"{name:<26}${gross:>10,.0f}${-slip_cost:>10,.0f}${-funding_cost:>8,.0f}${honest:>10,.0f}")

print("\npoint: same market exposure, same naive PnL, but flipping every hour = 48 fills ->")
print("      slippage cost is 24x buy-and-hold. Same move, overtrading hands the profit to slippage.")
print("      (BTC is deep so the gap is small; on a thin coin it explodes. Add funding and you get the 'live' picture.)")
print("\n!! honest caveat: historical per-moment book depth isn't in the API, so slippage uses the current book; a true replay would store historical book snapshots.")
