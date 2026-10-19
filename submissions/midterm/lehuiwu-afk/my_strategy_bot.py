"""my_strategy_bot.py — Inventory-Aware DEX Rebalancer

Original Track-B strategy:
- Read MAX/tUSDC prices on DEX-A and DEX-B.
- Read my own MAX and tUSDC balances.
- Keep the portfolio roughly balanced between MAX and tUSDC.
- If MAX exposure is too low, buy MAX on the cheaper DEX.
- If MAX exposure is too high, sell MAX on the more expensive DEX.
- Only act when the two DEX prices differ enough to make venue selection useful.
"""

import os
from chain import ADDR, at, erc20, send, ensure_allowance, acct_of

NAME = "inventory-rebalancer"

KEY = os.environ["AGENT_KEY"]
ME = acct_of(KEY).address

WAD = 10 ** 18

MIN_GAP_PCT = 0.50

# Desired MAX share of total portfolio value
TARGET_MAX_SHARE = 0.50

# Do nothing while inside this band
LOW_MAX_SHARE = 0.40
HIGH_MAX_SHARE = 0.55

# Only rebalance a small amount each time
TRADE_FRACTION = 0.01

_TOKEN0 = {}


def _token0(pool):
    if pool not in _TOKEN0:
        _TOKEN0[pool] = (
            at(ADDR[pool], "Pair")
            .functions.token0()
            .call()
            .lower()
        )
    return _TOKEN0[pool]


def _mx_usd(pool):
    """Return (MAX reserve, tUSDC reserve)."""
    r0, r1 = at(ADDR[pool], "Pair").functions.getReserves().call()

    if _token0(pool) == ADDR["MAX"].lower():
        return r0, r1

    return r1, r0


def scan():
    # ----- market prices -----
    A = _mx_usd("PoolA")
    B = _mx_usd("PoolB")

    pa = A[1] / A[0]       # tUSDC per MAX
    pb = B[1] / B[0]

    cheap_price = min(pa, pb)
    dear_price = max(pa, pb)

    gap_pct = (dear_price / cheap_price - 1) * 100

    if pa <= pb:
        cheap_router = "RouterA"
        dear_router = "RouterB"
        cheap_name = "DEX-A"
        dear_name = "DEX-B"
    else:
        cheap_router = "RouterB"
        dear_router = "RouterA"
        cheap_name = "DEX-B"
        dear_name = "DEX-A"

    # ----- my wallet -----
    usdc = erc20("tUSDC")
    mx = erc20("MAX")

    usdc_balance = usdc.functions.balanceOf(ME).call()
    max_balance = mx.functions.balanceOf(ME).call()

    # Use midpoint price to estimate MAX value
    mid_price = (pa + pb) / 2

    usdc_value = usdc_balance / WAD
    max_value = (max_balance / WAD) * mid_price

    total_value = usdc_value + max_value

    if total_value <= 0:
        return {
            "hit": False,
            "line": "inventory-rebalancer: wallet has no usable balance"
        }

    max_share = max_value / total_value

    # ----- decision -----
    action = "hold"
    router = None
    amount = 0

    if gap_pct >= MIN_GAP_PCT:

        # Too little MAX -> buy MAX at cheaper venue
        if max_share < LOW_MAX_SHARE and usdc_balance > 0:
            action = "buy"
            router = cheap_router
            amount = int(usdc_balance * TRADE_FRACTION)

        # Too much MAX -> sell MAX at more expensive venue
        elif max_share > HIGH_MAX_SHARE and max_balance > 0:
            action = "sell"
            router = dear_router
            amount = int(max_balance * TRADE_FRACTION)

    hit = action != "hold" and amount > 0

    line = (
        f"A {pa:.2f} / B {pb:.2f} | "
        f"gap {gap_pct:.2f}% | "
        f"MAX share {max_share * 100:.1f}% | "
        f"{action}"
    )

    return {
        "hit": hit,
        "line": line,
        "action": action,
        "router": router,
        "amount": amount,
        "gap": gap_pct,
        "cheap_name": cheap_name,
        "dear_name": dear_name,
        "max_share": max_share,
    }


def fire(s):
    router = at(ADDR[s["router"]], "Router")

    if s["action"] == "buy":

        ensure_allowance(
            "tUSDC",
            ADDR[s["router"]],
            key=KEY
        )

        rcpt = send(
            router.functions.swapExactTokensForTokens(
                s["amount"],
                0,
                ADDR["tUSDC"],
                ADDR["MAX"],
                ME
            ),
            key=KEY
        )

        result = "bought MAX on cheaper DEX"

    elif s["action"] == "sell":

        ensure_allowance(
            "MAX",
            ADDR[s["router"]],
            key=KEY
        )

        rcpt = send(
            router.functions.swapExactTokensForTokens(
                s["amount"],
                0,
                ADDR["MAX"],
                ADDR["tUSDC"],
                ME
            ),
            key=KEY
        )

        result = "sold MAX on more expensive DEX"

    else:
        raise RuntimeError("fire() called without a trade action")

    return {
        "tx": rcpt.transactionHash.hex(),
        "action": result,
        "gap": s["gap"],
    }
