"""Liquidity-aware MAX/tUSDC spread decision logic (pure Python, no RPC)."""

NAME = "zhenzhenfang-liquidity-aware"
WAD = 10**18
BPS = 10_000
SWAP_FEE_BPS = 30
MAX_TRADE_USDC = 5_000 * WAD
MAX_POOL_FRACTION_BPS = 200
MIN_USDC_RESERVE = 1_000 * WAD
MIN_NET_PROFIT_USDC = 2 * WAD
# The repository has no gas-to-tUSDC oracle. This is a conservative modeling
# reserve, not an on-chain gas conversion or a guarantee of net profit.
GAS_RESERVE_USDC = 1 * WAD
SEARCH_STEPS = 200


def amount_out(amount_in, reserve_in, reserve_out, fee_bps=SWAP_FEE_BPS):
    """Uniswap-v2 constant-product output, using integer math and round-down."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        return 0
    amount_with_fee = amount_in * (BPS - fee_bps)
    return amount_with_fee * reserve_out // (reserve_in * BPS + amount_with_fee)


def _route_profit(amount_in, cheap, dear):
    bought_max = amount_out(amount_in, cheap["usdc"], cheap["max"])
    received_usdc = amount_out(bought_max, dear["max"], dear["usdc"])
    return received_usdc - amount_in


def _best_size(cheap, dear, wallet_usdc):
    cap = min(
        MAX_TRADE_USDC,
        cheap["usdc"] * MAX_POOL_FRACTION_BPS // BPS,
        wallet_usdc,
    )
    if cap <= 0:
        return 0, 0, -GAS_RESERVE_USDC
    step = max(1, cap // SEARCH_STEPS)
    best_amount, best_gross = 0, 0
    for i in range(1, SEARCH_STEPS + 1):
        amount = min(i * step, cap)
        gross = _route_profit(amount, cheap, dear)
        if gross > best_gross:
            best_amount, best_gross = amount, gross
    return best_amount, best_gross, best_gross - GAS_RESERVE_USDC


def _empty(line, wallet=None):
    return {
        "hit": False,
        "line": line,
        "buy_pool": None,
        "sell_pool": None,
        "buy_router": None,
        "sell_router": None,
        "amount_in": 0,
        "estimated_gross_profit": 0,
        "estimated_net_profit": -GAS_RESERVE_USDC,
        "quoted_gap": 0.0,
        "wallet_address": wallet,
    }


def decide(view):
    """Return an original spread signal from a reserve and wallet snapshot.

    Expected view shape::

        {"reserves": {"PoolA": {"max": int, "usdc": int},
                      "PoolB": {"max": int, "usdc": int}},
         "wallet": {"address": str, "tusdc": int}}

    All token quantities are integer base units (18 decimals for these course
    tokens). This function only computes a signal; it never signs or sends.
    """
    if not isinstance(view, dict):
        return _empty("invalid view: expected a mapping")
    try:
        pools = view["reserves"]
        wallet = view["wallet"]
        address = wallet["address"]
        wallet_usdc = wallet["tusdc"]
        pool_a = {"name": "PoolA", "max": pools["PoolA"]["max"], "usdc": pools["PoolA"]["usdc"]}
        pool_b = {"name": "PoolB", "max": pools["PoolB"]["max"], "usdc": pools["PoolB"]["usdc"]}
    except (KeyError, TypeError):
        return _empty("invalid view: missing reserves or wallet fields")

    integer_values = (pool_a["max"], pool_a["usdc"], pool_b["max"], pool_b["usdc"], wallet_usdc)
    if (not isinstance(address, str) or not address
            or any(type(value) is not int or value < 0 for value in integer_values)
            or min(pool_a["max"], pool_a["usdc"], pool_b["max"], pool_b["usdc"]) == 0):
        return _empty("invalid view: address or integer reserve/balance values", address if isinstance(address, str) else None)

    liquid = pool_a["usdc"] >= MIN_USDC_RESERVE and pool_b["usdc"] >= MIN_USDC_RESERVE
    if pool_a["usdc"] * pool_b["max"] <= pool_b["usdc"] * pool_a["max"]:
        cheap, dear, buy_router, sell_router = pool_a, pool_b, "RouterA", "RouterB"
    else:
        cheap, dear, buy_router, sell_router = pool_b, pool_a, "RouterB", "RouterA"

    amount, gross, net = _best_size(cheap, dear, wallet_usdc)
    gap = (dear["usdc"] * cheap["max"] / (dear["max"] * cheap["usdc"])) - 1
    hit = liquid and amount > 0 and net >= MIN_NET_PROFIT_USDC
    line = (
        f"{NAME}: wallet={address}; A={pool_a['usdc']/pool_a['max']:.3f}, "
        f"B={pool_b['usdc']/pool_b['max']:.3f} tUSDC/MAX; gap={gap:.2%}; "
        f"size={amount/WAD:,.2f}; estimated gross={gross/WAD:+,.3f}, "
        f"estimated net after modeled gas reserve={net/WAD:+,.3f} tUSDC; "
        f"liquidity={pool_a['usdc']/WAD:,.0f}/{pool_b['usdc']/WAD:,.0f}; "
        f"signal={'HIT' if hit else 'skip'} (dry-run)"
    )
    return {
        "hit": hit,
        "line": line,
        "buy_pool": cheap["name"],
        "sell_pool": dear["name"],
        "buy_router": buy_router,
        "sell_router": sell_router,
        "amount_in": amount,
        "estimated_gross_profit": gross,
        "estimated_net_profit": net,
        "quoted_gap": gap,
        "liquid": liquid,
        "wallet_address": address,
        "wallet_tusdc": wallet_usdc,
    }
