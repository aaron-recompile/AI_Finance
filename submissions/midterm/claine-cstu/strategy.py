"""strategy.py — NexusRouter: Pure Mathematical & Decision Logic (Track B, claine-cstu).

This module contains only pure algorithmic decision logic:
- Zero RPC, zero network calls, zero private keys.
- Completely deterministically testable offline: run `python strategy.py`.

THE INEFFICIENCY EXPLOITED
The Base Sepolia arena hosts four constant-product venues quoting MAX/tUSDC:
    1. SimpleAMM pools : CHEAP, DEAR (~$6M depth each, static price ~2000 tUSDC/MAX)
    2. Uniswap-v2 pools : PoolA, PoolB (~$100k-$140k depth, volatile, ~400-500 tUSDC/MAX)
The built-in bots only arbitrage inside a single family (CHEAP<->DEAR or PoolA<->PoolB).
NexusRouter continuously evaluates all N x (N-1) directed pool permutations, dynamically
identifying cross-family structural dislocations.

OPTIMAL CONVEX SIZING (Analytical Derivation)
For a swap of D tUSDC on venue 1 (m1, u1) followed by selling the acquired MAX on
venue 2 (m2, u2) with swap fee factor gamma = 997/1000 = G/T:
    u_out(D) = (a * D) / (b + c * D)
where:
    a = G^2 * m1 * u2
    b = T^2 * m2 * u1
    c = G * T * m2 + G^2 * m1

Net profit P(D) = u_out(D) - D is strictly concave for D >= 0. Setting dP/dD = 0 yields:
    D* = (sqrt(a * b) - b) / c   (for a > b; D* = 0 if a <= b)
The capital-constrained optimal trade size for wallet budget W is:
    D_opt = min(D*, W)
"""
from math import isqrt

NAME = "nexus-router"

WAD = 10 ** 18
G, T = 9970, 10000                           # 0.30% Uniswap-v2 swap fee on all venues
MIN_PROFIT_WEI = 1 * WAD                     # Minimum absolute net profit: 1.0 tUSDC
MIN_EDGE_BPS = 20                            # Minimum return on capital: 20 bps (0.20%)
UNWIND_THRESHOLD = int(0.001 * WAD)          # If wallet holds >0.001 MAX, trigger self-unwind


def quote(amount_in: int, r_in: int, r_out: int) -> int:
    """Standard Uniswap constant-product output formula with 0.3% fee."""
    if amount_in <= 0 or r_in <= 0 or r_out <= 0:
        return 0
    amount_in_with_fee = amount_in * G
    numerator = amount_in_with_fee * r_out
    denominator = r_in * T + amount_in_with_fee
    return numerator // denominator


def optimal_in(buy_reserves: tuple[int, int], sell_reserves: tuple[int, int]) -> int:
    """Compute the analytical optimal input size D* in wei of tUSDC.
    
    buy_reserves  : (m1, u1) = (MAX reserve, tUSDC reserve) on the buy pool
    sell_reserves : (m2, u2) = (MAX reserve, tUSDC reserve) on the sell pool
    """
    (m1, u1), (m2, u2) = buy_reserves, sell_reserves
    if m1 <= 0 or u1 <= 0 or m2 <= 0 or u2 <= 0:
        return 0

    a = G * G * m1 * u2
    b = T * T * m2 * u1
    c = G * T * m2 + G * G * m1

    if a <= b or c <= 0:
        return 0

    # D* = (sqrt(a * b) - b) / c
    return (isqrt(a * b) - b) // c


def round_trip(D: int, buy_reserves: tuple[int, int], sell_reserves: tuple[int, int]) -> int:
    """Simulate tUSDC output after buying MAX with D tUSDC and selling all received MAX."""
    (m1, u1), (m2, u2) = buy_reserves, sell_reserves
    max_received = quote(D, u1, m1)
    if max_received <= 0:
        return 0
    return quote(max_received, m2, u2)


def best_exit(view: dict, max_amount: int) -> tuple[str, int]:
    """Identify which venue pays the maximum tUSDC for `max_amount` of MAX."""
    quotes = {
        venue: quote(max_amount, m, u)
        for venue, (m, u) in view["reserves"].items()
    }
    best_venue = max(quotes, key=quotes.get)
    return best_venue, quotes[best_venue]


def decide(view: dict) -> dict:
    """Evaluate current market state and choose optimal action: trade, unwind, or hold.
    
    view format:
        {
            "reserves": {venue: (max_reserve, usdc_reserve), ...},
            "usdc": int (wallet tUSDC in wei),
            "max": int (wallet MAX in wei)
        }
    """
    reserves = view["reserves"]
    usdc_balance = view.get("usdc", 0)
    max_balance = view.get("max", 0)

    # Compute mid prices for logging
    prices = {v: reserves[v][1] / reserves[v][0] for v in reserves}
    px_str = " | ".join(f"{v}: {prices[v]:.1f}" for v in sorted(reserves.keys()))

    # SAFETY / RECOVERY SHIELD:
    # If the bot holds stranded MAX inventory (e.g. from an interrupted leg or prior run),
    # prioritize unwinding to tUSDC at the best available venue before new trades.
    if max_balance >= UNWIND_THRESHOLD:
        exit_venue, est_usdc = best_exit(view, max_balance)
        line = (
            f"SAFETY UNWIND: {max_balance / WAD:.4f} stranded MAX -> "
            f"sell on {exit_venue} for est {est_usdc / WAD:,.2f} tUSDC"
        )
        return {
            "action": "unwind",
            "hit": True,
            "venue": exit_venue,
            "max_wei": max_balance,
            "max_units": max_balance / WAD,
            "est_usdc": est_usdc / WAD,
            "line": f"[{px_str}] => {line}",
        }

    # Evaluate all directed venue pairs
    best = None
    for buy_v, r_buy in reserves.items():
        for sell_v, r_sell in reserves.items():
            if buy_v == sell_v:
                continue

            d_star = optimal_in(r_buy, r_sell)
            if d_star <= 0:
                continue

            # Constrain to wallet capital
            d_trade = min(d_star, usdc_balance)
            if d_trade <= 0:
                continue

            u_out = round_trip(d_trade, r_buy, r_sell)
            net_profit = u_out - d_trade

            if best is None or net_profit > best["profit_wei"]:
                best = {
                    "buy": buy_v,
                    "sell": sell_v,
                    "d_star_wei": d_star,
                    "size_wei": d_trade,
                    "profit_wei": net_profit,
                    "est_out_wei": u_out,
                }

    if best is None:
        reason = "no profitable gap wider than fees" if usdc_balance > 0 else "zero tUSDC balance"
        return {
            "action": "hold",
            "hit": False,
            "line": f"[{px_str}] => HOLD ({reason})",
        }

    d_trade = best["size_wei"]
    profit = best["profit_wei"]

    # Minimum profit and minimum edge hurdles
    has_min_profit = profit >= MIN_PROFIT_WEI
    has_min_edge = (profit * 10000) >= (d_trade * MIN_EDGE_BPS)
    hit = has_min_profit and has_min_edge

    buy_px = prices[best["buy"]]
    sell_px = prices[best["sell"]]
    spread_pct = ((sell_px / buy_px) - 1.0) * 100.0

    line = (
        f"ARBITRAGE: Buy {best['buy']} ({buy_px:.1f}) -> Sell {best['sell']} ({sell_px:.1f}) | "
        f"spread +{spread_pct:.1f}% | size {d_trade / WAD:,.1f} tUSDC | "
        f"est profit +{profit / WAD:,.2f} tUSDC ({profit / d_trade * 100:.2f}%)"
    )

    return {
        "action": "trade" if hit else "hold",
        "hit": hit,
        "buy": best["buy"],
        "sell": best["sell"],
        "spread_pct": spread_pct,
        "size_wei": d_trade,
        "size": d_trade / WAD,
        "profit_wei": profit,
        "profit": profit / WAD,
        "line": f"[{px_str}] => {line}",
    }


if __name__ == "__main__":
    print(f"=== {NAME} Offline Self-Check ===")
    
    # 1. Synthetic test market
    test_market = {
        "reserves": {
            "CHEAP": (3000 * WAD, 6_000_000 * WAD),  # ~2000 tUSDC/MAX
            "DEAR":  (3000 * WAD, 6_000_000 * WAD),  # ~2000 tUSDC/MAX
            "PoolA": (330 * WAD, 145_000 * WAD),     # ~439.4 tUSDC/MAX
            "PoolB": (240 * WAD, 115_000 * WAD),     # ~479.2 tUSDC/MAX
        },
        "usdc": 1000 * WAD,
        "max": 0,
    }

    decision = decide(test_market)
    print("\nDecision with 1,000 tUSDC capital:")
    print("Action:", decision["action"])
    print("Hit:", decision["hit"])
    print("Line:", decision["line"])
    assert decision["hit"] is True
    assert decision["buy"] in ("PoolA", "PoolB")
    assert decision["sell"] in ("CHEAP", "DEAR")
    print("\n[OK] Sizing and directional routing passed.")

    # 2. Test stranded inventory safety shield
    test_stranded = {
        "reserves": test_market["reserves"],
        "usdc": 0,
        "max": 2 * WAD,
    }
    unwind_decision = decide(test_stranded)
    print("\nDecision with stranded 2.0 MAX:")
    print("Action:", unwind_decision["action"])
    print("Line:", unwind_decision["line"])
    assert unwind_decision["action"] == "unwind"
    assert unwind_decision["hit"] is True
    print("\n[OK] Stranded inventory unwind logic passed.")

    print("\nAll self-check tests passed successfully!")
