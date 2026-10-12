"""Liquidity-aware DEX spread monitor for the midterm strategy."""
import os
from chain import ADDR, at

NAME = "liquidity-aware-spread-monitor"

# No private key is required for read-only scanning.
KEY = os.environ.get("AGENT_KEY", "")

MIN_SPREAD = 0.01       # Require at least a 1% quoted price gap
MIN_LIQUIDITY = 1000    # Minimum tUSDC reserve in each pool
WAD = 10**18


def scan():
    """Read both pools and report a guarded spread signal."""
    pool_a = at(ADDR["PoolA"], "Pair")
    pool_b = at(ADDR["PoolB"], "Pair")

    def read_pool(pool, label):
        token0 = pool.functions.token0().call().lower()
        token1 = pool.functions.token1().call().lower()
        reserves = pool.functions.getReserves().call()

        if token0 != ADDR["MAX"].lower() or token1 != ADDR["tUSDC"].lower():
            raise RuntimeError(
                f"{label}: unexpected token order; refusing to calculate price"
            )

        max_reserve = reserves[0]
        usdc_reserve = reserves[1]

        if max_reserve <= 0 or usdc_reserve <= 0:
            raise RuntimeError(f"{label}: empty pool")

        price = usdc_reserve / max_reserve
        liquidity = usdc_reserve / WAD
        return price, liquidity

    price_a, liquidity_a = read_pool(pool_a, "PoolA")
    price_b, liquidity_b = read_pool(pool_b, "PoolB")

    lower = min(price_a, price_b)
    higher = max(price_a, price_b)
    spread = higher / lower - 1

    liquid_enough = (
        liquidity_a >= MIN_LIQUIDITY
        and liquidity_b >= MIN_LIQUIDITY
    )
    hit = spread >= MIN_SPREAD and liquid_enough

    line = (
        f"{NAME}: PoolA={price_a:.4f}, PoolB={price_b:.4f} "
        f"tUSDC/MAX; gap={spread:.2%}; "
        f"liquidity A/B={liquidity_a:.0f}/{liquidity_b:.0f} tUSDC; "
        f"signal={'HIT' if hit else 'skip'}"
    )

    return {
        "hit": hit,
        "line": line,
        "price_a": price_a,
        "price_b": price_b,
        "spread": spread,
        "liquidity_a": liquidity_a,
        "liquidity_b": liquidity_b,
    }


def fire(s):
    """Live trading is intentionally disabled until the strategy is reviewed."""
    raise RuntimeError(
        "Live trading is not implemented. Do not run this bot with --live."
    )
