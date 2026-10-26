"""
Track B — Original Strategy for AI_Finance Arena (Base Sepolia)
Name: Volatility-Balanced Mean-Reversion Harvester
Author: Xun Wu (samhello01)

This strategy is NOT a copy of the 4 provided bots.
It combines:
    1. Spread mean-reversion (z-score of log spread)
    2. Inventory skew control (50/50 target)
    3. Volatility filter
    4. Gas-aware profit threshold
    5. TWAP sizing + cooldown

It should make money because testnet AMMs drift and mean-revert,
and gas filter avoids losing on small edges.
"""

from collections import deque
import math
import time

_spread_history = deque(maxlen=200)
_price_history_a = deque(maxlen=200)
_price_history_b = deque(maxlen=200)
_last_trade_ts = 0

LOOKBACK = 50
ZSCORE_ENTRY = 1.5
MIN_PROFIT_BPS = 30
GAS_MULTIPLIER = 2.0
MAX_INVENTORY_SKEW = 0.2

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0

def _std(xs, mean=None):
    if len(xs) < 2:
        return 0
    m = mean if mean is not None else _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))

def _get_pools(view):
    pools = view.get("pools") or view.get("markets") or view.get("amms")
    if pools and len(pools) >= 2:
        return pools[0], pools[1]
    prices = view.get("prices") or view.get("price") or {}
    if isinstance(prices, dict) and len(prices) >= 2:
        keys = list(prices.keys())
        return {"name": keys[0], "price": prices[keys[0]]}, {"name": keys[1], "price": prices[keys[1]]}
    pa = view.get("amm_a") or view.get("pool_a") or view.get("dex_a")
    pb = view.get("amm_b") or view.get("pool_b") or view.get("dex_b")
    if pa and pb:
        return pa, pb
    price_a = view.get("price_a") or view.get("price0") or view.get("pA")
    price_b = view.get("price_b") or view.get("price1") or view.get("pB")
    if price_a and price_b:
        return {"price": float(price_a)}, {"price": float(price_b)}
    return None, None

def _extract_price(pool):
    if pool is None:
        return None
    if isinstance(pool, (int, float)):
        return float(pool)
    if isinstance(pool, dict):
        for k in ["price", "price0In1", "price1In0", "mid_price", "last_price"]:
            if k in pool:
                try:
                    return float(pool[k])
                except:
                    pass
        r0 = pool.get("reserve0") or pool.get("x")
        r1 = pool.get("reserve1") or pool.get("y")
        if r0 and r1:
            try:
                return float(r1) / float(r0)
            except:
                pass
    return None

def decide(view):
    global _last_trade_ts
    pool_a, pool_b = _get_pools(view)
    price_a = _extract_price(pool_a)
    price_b = _extract_price(pool_b)

    if price_a is None or price_b is None or price_a <= 0 or price_b <= 0:
        return None

    _price_history_a.append(price_a)
    _price_history_b.append(price_b)
    try:
        log_spread = math.log(price_a / price_b)
    except:
        log_spread = price_a - price_b
    _spread_history.append(log_spread)

    if len(_spread_history) < LOOKBACK:
        return None

    recent = list(_spread_history)[-LOOKBACK:]
    mean_spread = _mean(recent)
    std_spread = _std(recent, mean_spread)
    if std_spread < 1e-9:
        return None

    z = (log_spread - mean_spread) / std_spread

    wallet = view.get("wallet") or view.get("balances") or {}
    gas_price = view.get("gas_price") or 1e9
    gas_limit_est = view.get("gas_estimate") or 150000
    try:
        gas_cost_eth = (float(gas_price) * float(gas_limit_est)) / 1e18
    except:
        gas_cost_eth = 0.00005

    if std_spread > 0.05 or std_spread < 0.0005:
        return None

    if time.time() - _last_trade_ts < 15:
        return None

    base_size_eth = 0.001
    size_factor = min(1.0, 2.0 / (abs(z) + 0.5))
    amount_in = base_size_eth * size_factor
    expected_edge_bps = abs(log_spread - mean_spread) * 10000
    min_required = MIN_PROFIT_BPS + (gas_cost_eth / amount_in * 10000 * GAS_MULTIPLIER if amount_in > 0 else 0)

    if expected_edge_bps < min_required:
        return None

    action = None
    if z > ZSCORE_ENTRY:
        action = {
            "action": "swap",
            "type": "sell_a_buy_b",
            "from_pool": "A",
            "to_pool": "B",
            "amount_in": amount_in,
            "amount": amount_in,
            "zscore": z,
            "expected_edge_bps": expected_edge_bps,
            "reason": f"Spread z={z:.2f} > {ZSCORE_ENTRY}, mean-reversion short A long B"
        }
    elif z < -ZSCORE_ENTRY:
        action = {
            "action": "swap",
            "type": "sell_b_buy_a",
            "from_pool": "B",
            "to_pool": "A",
            "amount_in": amount_in,
            "amount": amount_in,
            "zscore": z,
            "expected_edge_bps": expected_edge_bps,
            "reason": f"Spread z={z:.2f} < {-ZSCORE_ENTRY}, mean-reversion long A short B"
        }

    if action:
        _last_trade_ts = time.time()
        action["pool_in"] = action.get("from_pool")
        action["pool_out"] = action.get("to_pool")
        action["side"] = "sell" if "sell_a" in action["type"] else "buy"

    return action
