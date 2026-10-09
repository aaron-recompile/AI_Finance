# ---------------------------------------------------------------
# Historical data (the foundation for a replay cursor, read-only):
#   A. candles (candleSnapshot)      -- price history, step forward one bar at a time
#   B. funding history (fundingHistory) -- how carry changes over time (arb timing)
# Run:  python hl_history.py [COIN]   default BTC
# ---------------------------------------------------------------
import sys, time
from hyperliquid.info import Info
from hyperliquid.utils import constants

COIN = sys.argv[1] if len(sys.argv) > 1 else "BTC"
NOW = int(time.time() * 1000)
DAY = 24 * 3600 * 1000

info = Info(constants.MAINNET_API_URL, skip_ws=True)

# -- A. candles: last 24h of 1h bars --
print("=" * 62)
print(f"A. {COIN} last 24h . 1h candles (the price base for replay)")
print("=" * 62)
candles = info.candles_snapshot(COIN, "1h", NOW - DAY, NOW)
print(f"{'time (UTC)':<16}{'open':>10}{'high':>10}{'low':>10}{'close':>10}{'vol':>12}")
for c in candles[-8:]:                       # last 8 bars
    t = time.strftime("%m-%d %H:%M", time.gmtime(c["t"] / 1000))
    print(f"{t:<16}{float(c['o']):>10,.1f}{float(c['h']):>10,.1f}{float(c['l']):>10,.1f}{float(c['c']):>10,.1f}{float(c['v']):>12,.2f}")
o24, c_now = float(candles[0]["o"]), float(candles[-1]["c"])
hi = max(float(c["h"]) for c in candles); lo = min(float(c["l"]) for c in candles)
print(f"\n  24h: open {o24:,.1f} -> close {c_now:,.1f}  ({(c_now/o24-1)*100:+.2f}%)  range [{lo:,.1f}, {hi:,.1f}]  {len(candles)} bars")

# -- B. funding history: last 24h, hourly --
print("\n" + "=" * 62)
print(f"B. {COIN} last 24h funding history (carry over time)")
print("=" * 62)
fh = info.funding_history(COIN, NOW - DAY, NOW)
rates = [float(x["fundingRate"]) for x in fh]
if rates:
    print(f"{'time (UTC)':<16}{'hourly':>12}{'annual':>10}")
    for x in fh[-8:]:
        t = time.strftime("%m-%d %H:%M", time.gmtime(x["time"] / 1000))
        r = float(x["fundingRate"])
        print(f"{t:<16}{r*100:>11.4f}%{r*24*365*100:>9.1f}%")
    avg = sum(rates) / len(rates)
    print(f"\n  {len(rates)} points  avg {avg*100:.4f}%/h (annual {avg*24*365*100:+.1f}%)"
          f"  range [{min(rates)*24*365*100:+.1f}%, {max(rates)*24*365*100:+.1f}%]")
    print("  -> arb timing: funding is not constant; enter the 'collecting' side when it's high, exit when it's low/flips.")

print("\nput together = the replay-cursor base: step bar by bar (price) + each fill at mid+slippage (hl_signals) + settle funding on the position each hour (carry).")
