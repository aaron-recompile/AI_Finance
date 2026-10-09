#!/usr/bin/env python3
"""Trend-following (MA50): hold when price is above its 50-day average, otherwise stay flat.
"Up keeps going up." Rides big trends, gives up a little in chop; acts like crash insurance.

Run:  python3 trend_follow.py          # BTC-USDT by default
      python3 trend_follow.py ETH-USDT
"""
import sys
from _common import backtest


def signal(closes, n=50):
    sig = []
    for i in range(len(closes)):
        if i < n:                                 # not enough history for the MA yet
            sig.append(0)
            continue
        ma = sum(closes[i - n + 1:i + 1]) / n
        sig.append(1 if closes[i] > ma else 0)
    return sig


if __name__ == "__main__":
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    backtest("Trend MA50", signal, inst)
