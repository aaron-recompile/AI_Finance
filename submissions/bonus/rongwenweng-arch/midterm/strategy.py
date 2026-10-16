"""strategy.py — CrossFamilyRouter: the decision logic (Track B mid-term, Rongwen Weng).

This file is the strategy itself and nothing else: no RPC, no wallet, no transactions.
`decide(view)` takes a snapshot of the market and answers "what should I do right now?".
`my_strategy_bot.py` is the thin on-chain adapter that builds the view and executes the answer.

IDEA
  The arena quotes MAX/tUSDC on FOUR venues that belong to two separate "families":
      flash-demo AMMs   : CHEAP, DEAR
      Uniswap-v2 style  : PoolA, PoolB
  The provided bots only arbitrage INSIDE a family (swap-arb: CHEAP<->DEAR,
  dex-arb: PoolA<->PoolB). Nobody connects the two families, so a gap BETWEEN them
  just sits there. This strategy treats all four as one market.

VIEW
    {"reserves": {venue: (MAX reserve, tUSDC reserve), ...},   # wei, any number of venues
     "usdc": my tUSDC balance in wei}

Run this file directly for an offline self-check (no chain needed):
    python strategy.py
"""
from math import isqrt

NAME = "cross-family-router"

WAD = 10 ** 18
G, T = 9970, 10000                           # 0.3% swap fee on every venue: keep G/T
MIN_PROFIT = 1 * WAD                         # don't fire for less than 1 tUSDC
MIN_EDGE_BPS = 20                            # ...or for less than 0.20% of the trade size


def quote(amount_in, r_in, r_out):
    """Constant-product quote with the 0.3% fee — same formula the contracts use."""
    a = amount_in * G
    return a * r_out // (r_in * T + a)


def optimal_in(buy, sell):
    """Best tUSDC size for: buy MAX on `buy` (m1,u1), sell it on `sell` (m2,u2).

    Chaining the two swaps gives   usd_out(D) = a*D / (b + c*D)   with
        a = G^2*m1*u2,   b = T^2*m2*u1,   c = G*T*m2 + G^2*m1
    Profit usd_out(D) - D peaks where d(usd_out)/dD = 1, i.e.  D* = (sqrt(a*b) - b) / c.
    a <= b means the gap is smaller than the two fees: no trade.
    """
    (m1, u1), (m2, u2) = buy, sell
    a, b, c = G * G * m1 * u2, T * T * m2 * u1, G * T * m2 + G * G * m1
    return (isqrt(a * b) - b) // c if a > b else 0


def round_trip(D, buy, sell):
    """tUSDC back after spending D tUSDC on `buy` and selling the MAX on `sell`."""
    (m1, u1), (m2, u2) = buy, sell
    return quote(quote(D, u1, m1), m2, u2)


def decide(view):
    """Look at every venue at once and pick the single best buy -> sell route.

    Tries every ordered (buy venue, sell venue) pair, sizes each with the closed-form
    optimum capped by my own balance, and keeps the pair with the highest net profit.
    Returns {"action": "trade", "buy", "sell", "size_wei", ...} or {"action": "hold", ...}.
    """
    R, budget = view["reserves"], view["usdc"]
    px = {v: R[v][1] / R[v][0] for v in R}                       # tUSDC per MAX
    best = None
    for b in R:
        for s in R:
            if b == s:
                continue
            D = min(optimal_in(R[b], R[s]), budget)              # can't trade more than I hold
            if D <= 0:
                continue
            profit = round_trip(D, R[b], R[s]) - D
            if best is None or profit > best["profit_wei"]:
                best = {"buy": b, "sell": s, "size_wei": D, "profit_wei": profit}
    prices = " ".join(f"{v} {px[v]:.0f}" for v in R)
    if best is None:
        why = "no gap wider than fees" if budget > 0 else "no tUSDC to trade with"
        return {"action": "hold", "hit": False, "line": f"{prices} | {why}"}
    D, p = best["size_wei"], best["profit_wei"]
    hit = p >= MIN_PROFIT and p * 10000 >= D * MIN_EDGE_BPS
    gap = (px[best["sell"]] / px[best["buy"]] - 1) * 100
    return {"action": "trade" if hit else "hold", "hit": hit,
            "buy": best["buy"], "sell": best["sell"], "gap": gap,
            "size_wei": D, "size": D / WAD, "profit_wei": p, "profit": p / WAD,
            "line": f"{prices} | buy {best['buy']} -> sell {best['sell']} gap {gap:.2f}% "
                    f"| size {D/WAD:,.0f} | est {p/WAD:+,.2f} tUSDC"}


def best_exit(view, max_amount):
    """Leg 2 re-route: which venue pays the most tUSDC for `max_amount` MAX right now?"""
    quotes = {v: quote(max_amount, m, u) for v, (m, u) in view["reserves"].items()}
    venue = max(quotes, key=quotes.get)
    return venue, quotes[venue]


if __name__ == "__main__":
    # Offline self-check on a made-up market shaped like the arena (prices in tUSDC per MAX).
    def pool(max_units, price):
        return (max_units * WAD, max_units * price * WAD)

    view = {"reserves": {"CHEAP": pool(100, 1972), "DEAR": pool(100, 2023),
                         "PoolA": pool(100, 1750), "PoolB": pool(100, 1760)},
            "usdc": 2_000 * WAD}
    d = decide(view)
    print(d["line"], "->", d["action"])
    assert (d["action"], d["buy"], d["sell"]) == ("trade", "PoolA", "DEAR")

    # the closed-form size really is the peak: one step either side earns no more
    buy, sell = view["reserves"]["PoolA"], view["reserves"]["DEAR"]
    D = optimal_in(buy, sell)
    peak = round_trip(D, buy, sell) - D
    for step in (-WAD, WAD):
        assert round_trip(D + step, buy, sell) - (D + step) <= peak

    # equal prices everywhere: fees eat any trade, so hold
    flat = {"reserves": {v: pool(100, 2000) for v in view["reserves"]}, "usdc": 2_000 * WAD}
    assert decide(flat)["action"] == "hold"

    # the re-route sells where MAX is dearest
    assert best_exit(view, WAD)[0] == "DEAR"
    print("self-check ok")
