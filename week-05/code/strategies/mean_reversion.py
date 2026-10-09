#!/usr/bin/env python3
"""Mean-reversion (RSI(2)): buy when oversold (RSI < 10), sell the bounce (RSI > 70).
"Overshoots snap back." High win rate, small winners, very sensitive to trading costs.

Run:  python3 mean_reversion.py          # BTC-USDT by default
      python3 mean_reversion.py SPY       # (if you have that market's candles)
"""
import sys
from _common import backtest, rsi


def signal(closes, n=2, entry=10, exit=70):
    r = rsi(closes, n)
    sig, holding = [], 0
    for v in r:
        if v is None:
            sig.append(0)
            continue
        if holding == 0 and v < entry:           # oversold -> enter
            holding = 1
        elif holding == 1 and v > exit:          # bounced -> leave
            holding = 0
        sig.append(holding)
    return sig


if __name__ == "__main__":
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    backtest("Revert RSI(2) 10/70", signal, inst)
