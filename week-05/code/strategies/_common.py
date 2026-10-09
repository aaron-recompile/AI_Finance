"""Shared helpers for the simple strategy scripts: fetch daily candles from OKX (public, no key),
an RSI function, and a tiny open-to-open backtest. Stdlib only.

A strategy here = a function that takes the list of closes and returns a signal list (1 hold / 0 flat).
The backtest fills signal[t] at t+1's OPEN -- no look-ahead.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "okx"))
from okx_client import req


def fetch_daily(inst="BTC-USDT", limit=300):
    """Daily candles from OKX public market data. Returns (opens, closes), oldest first."""
    r = req("GET", f"/api/v5/market/candles?instId={inst}&bar=1D&limit={limit}", private=False)
    rows = list(reversed(r["data"]))        # OKX returns newest first -> flip to chronological
    opens = [float(c[1]) for c in rows]
    closes = [float(c[4]) for c in rows]
    return opens, closes


def rsi(closes, n):
    """Wilder-smoothed RSI, 0-100. Returns a list aligned to closes (first value None)."""
    out = [None]
    up = dn = 0.0
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gain, loss = max(d, 0.0), max(-d, 0.0)
        if i == 1:
            up, dn = gain, loss
        else:
            up = (up * (n - 1) + gain) / n
            dn = (dn * (n - 1) + loss) / n
        out.append(100 - 100 / (1 + up / dn) if dn else 100.0)
    return out


def backtest(name, signal_fn, inst="BTC-USDT", cost=0.0008):
    """Fetch data, run the strategy, print an honest open-to-open backtest vs buy-and-hold."""
    opens, closes = fetch_daily(inst)
    sig = signal_fn(closes)
    strat = hold = 1.0
    peak_s = peak_b = 1.0
    dd_s = dd_b = 0.0
    turns = inmkt = 0
    prev_pos = 0
    n = len(opens) - 1
    for t in range(n):
        pos = sig[t - 1] if t > 0 else 0          # today's position = yesterday's signal (no look-ahead)
        ret = opens[t + 1] / opens[t] - 1         # open-to-open return
        if pos != prev_pos:
            turns += 1
            strat *= (1 - cost)                   # pay one one-side cost on each rebalance
        prev_pos = pos
        inmkt += pos
        strat *= (1 + pos * ret)
        hold *= (1 + ret)
        peak_s = max(peak_s, strat); dd_s = min(dd_s, strat / peak_s - 1)
        peak_b = max(peak_b, hold);  dd_b = min(dd_b, hold / peak_b - 1)
    print(f"=== {name}  on {inst}  (daily, {n} bars, one-side cost {cost:.2%}) ===")
    print(f"  strategy : total {strat - 1:+.1%}   maxDD {dd_s:+.1%}   in-market {inmkt / n:.0%}   rebalances {turns}")
    print(f"  buy&hold : total {hold - 1:+.1%}   maxDD {dd_b:+.1%}")
    print(f"  today's signal: {'HOLD' if sig[-1] else 'FLAT'}  (you'd act at tomorrow's open)")
    print(f"  note: this strategy BETS ON DIRECTION. cash_and_carry.py does not.")
