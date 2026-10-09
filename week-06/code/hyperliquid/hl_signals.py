# ---------------------------------------------------------------
# Reading the book, deeper (read-only, no funds):
#   A. funding-rate screener -- find the most extreme carry perps (where arb comes from)
#   B. slippage estimator    -- how deep a market order eats, how far avg drifts from mid
# Use mainnet (real liquidity, numbers mean something); testnet is too thin for interpretation
# Run:  python hl_signals.py
# ---------------------------------------------------------------
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)
meta, ctxs = info.meta_and_asset_ctxs()
universe = meta["universe"]

# -- A. funding screen (annualized, sorted by |funding|, filtering out illiquid) --
print("=" * 60)
print("A. funding extremes (annualized; only counts OI > $5M)")
print("=" * 60)
rows = []
for a, c in zip(universe, ctxs):
    try:
        fh = float(c["funding"])                       # hourly rate
        mark = float(c["markPx"])
        oi_usd = float(c["openInterest"]) * mark
    except (KeyError, ValueError, TypeError):
        continue
    if oi_usd > 5e6:
        rows.append((a["name"], fh, fh * 24 * 365, oi_usd))

rows.sort(key=lambda r: abs(r[1]), reverse=True)
print(f"{'coin':<7}{'hourly':>10}{'annual':>10}{'OI':>9}   who pays whom / how to collect")
for name, fh, fy, oi in rows[:10]:
    who = "longs pay shorts -> short this side to collect funding" if fh > 0 else "shorts pay longs -> long this side to collect funding"
    print(f"{name:<7}{fh*100:>9.4f}%{fy*100:>9.1f}%{oi/1e6:>7.0f}M   {who}")

print("\n  arb in a nutshell: find a big |annual|, perp on one side + opposite hedge (spot / another venue's perp) = delta-neutral, net the funding.")

# -- B. slippage estimate: walk a market order through the book, compute avg vs mid --
def slippage(coin, usd, is_buy):
    book = info.l2_snapshot(coin)
    bids, asks = book["levels"][0], book["levels"][1]
    mid = (float(bids[0]["px"]) + float(asks[0]["px"])) / 2
    levels = asks if is_buy else bids          # a buy eats asks, a sell eats bids
    remaining, cost, filled_sz = usd, 0.0, 0.0
    for lvl in levels:
        px, sz = float(lvl["px"]), float(lvl["sz"])
        take = min(remaining, px * sz)
        filled_sz += take / px
        cost += take
        remaining -= take
        if remaining <= 0:
            break
    if filled_sz == 0:
        return mid, None, None, 0.0, usd
    avg = cost / filled_sz
    slip = (avg - mid) / mid * 1e4 * (1 if is_buy else -1)
    return mid, avg, slip, usd - remaining, remaining

for coin in ("BTC", "ETH"):
    print("\n" + "=" * 60)
    print(f"B. slippage estimate -- market BUY {coin} (eats asks)")
    print("=" * 60)
    for usd in (1e3, 1e4, 1e5, 1e6, 5e6):
        mid, avg, slip, filled, rem = slippage(coin, usd, True)
        if avg is None:
            continue
        tail = "" if rem <= 1 else f"  !! book only had ${filled:,.0f}, ${rem:,.0f} would eat through"
        print(f"  buy ${usd:>11,.0f}:  avg {avg:>10,.1f}   slip {slip:>+7.2f} bps{tail}")
    print(f"  (mid ~= {mid:,.1f}; slip = how much your avg beats the mid, in bps = 1/10000)")
