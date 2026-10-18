"""Liquidity-aware MAX/tUSDC spread scanner and guarded test-swap workflow.

The Router interface does not expose atomic two-pool arbitrage. ``fire`` can
only make one deliberately small tUSDC -> MAX swap to verify execution; this is
not an arbitrage and leaves the wallet exposed to MAX price risk.
"""
import os
import sys
import threading

from web3 import Web3
from chain import ADDR, CHAIN_ID, acct_of, at, erc20, send, w3

NAME = "liquidity-aware-spread"

# The course's ERC-20 and AMM sources use 18-decimal token units. Keep all
# amounts as integers; convert only for display.
WAD = 10**18
BPS = 10_000
SWAP_FEE_BPS = 30  # 0.30%, documented by the course AMM implementation.
MAX_TRADE_USDC = 5_000 * WAD
MAX_POOL_FRACTION_BPS = 200  # use at most 2% of cheaper pool's tUSDC reserve
MIN_USDC_RESERVE = 1_000 * WAD
MIN_NET_PROFIT_USDC = 2 * WAD
# The router/chain ABI gives no tUSDC-denominated gas oracle. This fixed reserve
# is only a placeholder, not a measured gas quote.
GAS_RESERVE_USDC = 1 * WAD
SEARCH_STEPS = 200
TEST_SWAP_USDC = 1 * WAD
MAX_SLIPPAGE_BPS = 100  # explicit 1% tolerance relative to the fresh AMM quote
MAX_GAS_LIMIT = 800_000
GAS_LIMIT_BUFFER_BPS = 2_000  # 20% estimate buffer
COURSE_AUTH_ENV = "COURSE_TEST_SWAP_AUTHORIZED"
UNLIMITED_ALLOWANCE_ACK_ENV = "ALLOW_UNLIMITED_ALLOWANCE_CONFIRMED"
UINT256_MAX = 2**256 - 1

# run.py keeps this module loaded while it loops. Serialize fire() and latch
# immediately before the first send attempt so a persistent HIT cannot trigger
# another transaction in the same bot process (even if receipt verification
# later fails). A restarted process is a new session and needs separate policy.
_fire_lock = threading.Lock()
_send_attempted = False

_DECIMALS_ABI = [{
    "name": "decimals", "type": "function", "stateMutability": "view",
    "inputs": [], "outputs": [{"type": "uint8"}],
}]


def amount_out(amount_in, reserve_in, reserve_out, fee_bps=SWAP_FEE_BPS):
    """Uniswap-v2 constant-product quote, rounded down like Solidity uint math."""
    if amount_in <= 0 or reserve_in <= 0 or reserve_out <= 0:
        return 0
    amount_with_fee = amount_in * (BPS - fee_bps)
    return amount_with_fee * reserve_out // (reserve_in * BPS + amount_with_fee)


def _read_pool(name):
    pair = at(ADDR[name], "Pair")
    token0 = pair.functions.token0().call().lower()
    token1 = pair.functions.token1().call().lower()
    max_addr, usdc_addr = ADDR["MAX"].lower(), ADDR["tUSDC"].lower()
    if {token0, token1} != {max_addr, usdc_addr}:
        raise RuntimeError(f"{name}: pair does not contain exactly MAX and tUSDC")
    reserve0, reserve1 = pair.functions.getReserves().call()
    if token0 == max_addr:
        max_reserve, usdc_reserve = reserve0, reserve1
    else:
        max_reserve, usdc_reserve = reserve1, reserve0
    if max_reserve <= 0 or usdc_reserve <= 0:
        raise RuntimeError(f"{name}: empty MAX/tUSDC pool")
    return {"name": name, "max": max_reserve, "usdc": usdc_reserve}


def _route_profit(amount_in, cheap, dear):
    bought_max = amount_out(amount_in, cheap["usdc"], cheap["max"])
    received_usdc = amount_out(bought_max, dear["max"], dear["usdc"])
    return received_usdc - amount_in


def _best_size(cheap, dear):
    cap = min(MAX_TRADE_USDC,
              cheap["usdc"] * MAX_POOL_FRACTION_BPS // BPS)
    step = max(1, cap // SEARCH_STEPS)
    best_amount, best_gross = 0, 0
    for i in range(1, SEARCH_STEPS + 1):
        amount = min(i * step, cap)
        gross = _route_profit(amount, cheap, dear)
        if gross > best_gross:
            best_amount, best_gross = amount, gross
    net = best_gross - GAS_RESERVE_USDC
    return best_amount, best_gross, net


def scan():
    """Read pools and report an estimated opportunity after fee/slippage model."""
    pool_a, pool_b = _read_pool("PoolA"), _read_pool("PoolB")
    liquid = (pool_a["usdc"] >= MIN_USDC_RESERVE
              and pool_b["usdc"] >= MIN_USDC_RESERVE)

    # Integer cross multiplication avoids float comparisons for direction/gap.
    if pool_a["usdc"] * pool_b["max"] <= pool_b["usdc"] * pool_a["max"]:
        cheap, dear, buy_router, sell_router = pool_a, pool_b, "RouterA", "RouterB"
    else:
        cheap, dear, buy_router, sell_router = pool_b, pool_a, "RouterB", "RouterA"

    amount, gross_profit, net_profit = _best_size(cheap, dear)
    low_num, low_den = cheap["usdc"], cheap["max"]
    high_num, high_den = dear["usdc"], dear["max"]
    # Float used only in presentation; all decisions and quotes remain integer.
    gap = (high_num * low_den / (high_den * low_num)) - 1
    hit = liquid and amount > 0 and net_profit >= MIN_NET_PROFIT_USDC
    line = (
        f"{NAME}: A={pool_a['usdc']/pool_a['max']:.3f}, "
        f"B={pool_b['usdc']/pool_b['max']:.3f} tUSDC/MAX; "
        f"gap={gap:.2%}; size={amount/WAD:,.2f}; "
        f"gross={gross_profit/WAD:+,.3f}, net after gas reserve="
        f"{net_profit/WAD:+,.3f} tUSDC; liquidity="
        f"{pool_a['usdc']/WAD:,.0f}/{pool_b['usdc']/WAD:,.0f}; "
        f"signal={'HIT' if hit else 'skip'} (scan only)"
    )
    return {
        "hit": hit,
        "line": line,
        "buy_pool": cheap["name"],
        "sell_pool": dear["name"],
        "buy_router": buy_router,
        "sell_router": sell_router,
        "amount_in": amount,
        "estimated_gross_profit": gross_profit,
        "estimated_net_profit": net_profit,
        "quoted_gap": gap,
        "liquid": liquid,
    }


def _execution_account():
    """Require the explicitly configured bot wallet; never use chain defaults."""
    key = os.environ.get("AGENT_KEY", "")
    if not key:
        raise RuntimeError("AGENT_KEY is unset; execution refused")
    configured_address = os.environ.get("AGENT_ADDRESS", "")
    if not configured_address:
        raise RuntimeError(
            "AGENT_ADDRESS is unset; set it to the supplied dedicated bot wallet"
        )
    try:
        account = acct_of(key)
        expected = Web3.to_checksum_address(configured_address)
    except Exception:
        raise RuntimeError("AGENT_KEY or AGENT_ADDRESS is malformed; execution refused") from None
    if account.address != expected:
        raise RuntimeError("AGENT_KEY does not match AGENT_ADDRESS; execution refused")
    return key, account.address


def _token_decimals(address):
    token = w3.eth.contract(
        address=Web3.to_checksum_address(address), abi=_DECIMALS_ABI
    )
    return token.functions.decimals().call()


def _minimum_output(quoted_out, slippage_bps=MAX_SLIPPAGE_BPS):
    """Return a positive integer min-out, rounded down like the router ABI."""
    if quoted_out <= 0 or not 0 <= slippage_bps < BPS:
        raise ValueError("quote must be positive and slippage must be below 10000 bps")
    min_out = quoted_out * (BPS - slippage_bps) // BPS
    if min_out <= 0:
        raise ValueError("minimum output rounded to zero")
    return min_out


def _bounded_gas_limit(estimated_gas):
    """Add a 20%/10k buffer and refuse values above the configured hard cap."""
    if estimated_gas <= 0:
        raise ValueError("gas estimate must be positive")
    gas_limit = max(
        estimated_gas + 10_000,
        (estimated_gas * (BPS + GAS_LIMIT_BUFFER_BPS) + BPS - 1) // BPS,
    )
    if gas_limit > MAX_GAS_LIMIT:
        raise RuntimeError("Estimated gas exceeds the configured cap; execution refused")
    return gas_limit


def fire(s):
    """Allow at most one send attempt for this imported bot process."""
    global _send_attempted
    if not _fire_lock.acquire(blocking=False):
        raise RuntimeError("Another fire() call is active; execution refused")
    try:
        if _send_attempted:
            raise RuntimeError(
                "This bot process already attempted a transaction; restart is required "
                "for a new explicitly reviewed session"
            )
        return _fire_once(s)
    finally:
        _fire_lock.release()


def _fire_once(s):
    """Prepare and, only after interactive per-transaction approval, send one test swap.

    This single tUSDC -> MAX swap validates the wallet execution path; it does
    not complete the cross-pool arbitrage strategy. A positive MAX position is
    intentionally left open and can lose value. No allowance is created here.
    """
    if not isinstance(s, dict) or not s.get("hit"):
        raise RuntimeError("No active scan opportunity; execution refused")
    key, recipient = _execution_account()
    if os.environ.get(COURSE_AUTH_ENV) != "YES":
        raise RuntimeError(
            f"Bot-specific course-action gate is unset; set {COURSE_AUTH_ENV}=YES "
            "only after confirming this action is permitted in the course arena"
        )
    if w3.eth.chain_id != CHAIN_ID:
        raise RuntimeError(f"Wrong chain ID; expected {CHAIN_ID}, execution refused")

    # Re-scan immediately before quoting; do not trust a stale caller snapshot.
    fresh = scan()
    if not fresh["hit"]:
        raise RuntimeError("Opportunity no longer clears the scan threshold; execution refused")
    route_fields = ("buy_pool", "sell_pool", "buy_router", "sell_router", "amount_in")
    if any(field not in s or s[field] != fresh[field] for field in route_fields):
        raise RuntimeError(
            "Scan signal is incomplete or its direction, route, or size changed; "
            "execution refused"
        )

    buy_pool = fresh["buy_pool"]
    router_name = fresh["buy_router"]
    pool = _read_pool(buy_pool)
    router_address = Web3.to_checksum_address(ADDR[router_name])
    pair_address = Web3.to_checksum_address(ADDR[buy_pool])
    usdc_address = Web3.to_checksum_address(ADDR["tUSDC"])
    max_address = Web3.to_checksum_address(ADDR["MAX"])

    for label, address in (("router", router_address), ("pair", pair_address),
                           ("tUSDC", usdc_address), ("MAX", max_address)):
        if not w3.eth.get_code(address):
            raise RuntimeError(f"No contract code at configured {label} address; execution refused")
    if _token_decimals(usdc_address) != 18 or _token_decimals(max_address) != 18:
        raise RuntimeError("Unexpected token decimals; expected 18 for both course tokens")

    amount_in = TEST_SWAP_USDC
    quoted_out = amount_out(amount_in, pool["usdc"], pool["max"])
    try:
        min_out = _minimum_output(quoted_out)
    except ValueError:
        raise RuntimeError("Quote/minimum output is invalid; execution refused") from None

    usdc = erc20("tUSDC")
    max_token = erc20("MAX")
    usdc_balance = usdc.functions.balanceOf(recipient).call()
    allowance = usdc.functions.allowance(recipient, router_address).call()
    if usdc_balance < amount_in:
        raise RuntimeError("Bot wallet lacks the test-swap tUSDC amount; execution refused")
    if allowance < amount_in:
        raise RuntimeError(
            f"Allowance is insufficient for this swap. Required: exactly "
            f"{amount_in / WAD:.6f} tUSDC ({amount_in} base units) to "
            f"{router_name} at {router_address}. No approval was sent. "
            "A new approval is a separate on-chain transaction and exposes this "
            "amount to the router; stop here and obtain explicit approval before "
            "creating it."
        )
    if (allowance == UINT256_MAX
            and os.environ.get(UNLIMITED_ALLOWANCE_ACK_ENV) != "YES"):
        raise RuntimeError(
            "Unlimited RouterA allowance requires separate local owner acknowledgement; "
            "execution refused. "
            f"Set {UNLIMITED_ALLOWANCE_ACK_ENV}=YES only after confirming owner intent "
            "and accepting the risk. No approval was changed."
        )

    router = at(router_address, "Router")
    swap_fn = router.functions.swapExactTokensForTokens(
        amount_in, min_out, usdc_address, max_address, recipient
    )
    try:
        estimated_gas = swap_fn.estimate_gas({"from": recipient})
    except Exception:
        raise RuntimeError("Gas estimate or preflight read failed; execution refused") from None
    gas_limit = _bounded_gas_limit(estimated_gas)
    try:
        gas_price = w3.eth.gas_price
        max_gas_cost = gas_limit * gas_price
        native_balance = w3.eth.get_balance(recipient)
    except Exception:
        raise RuntimeError("Gas estimate or preflight read failed; execution refused") from None
    if native_balance < max_gas_cost:
        raise RuntimeError("Bot wallet lacks the maximum estimated gas balance; execution refused")
    if not sys.stdin.isatty():
        raise RuntimeError("Interactive approval is required; no transaction was sent")

    ideal_out = amount_in * pool["max"] // pool["usdc"]
    modeled_impact_bps = (BPS - quoted_out * BPS // ideal_out) if ideal_out else BPS
    amount_text = f"{amount_in / WAD:.6f}"
    expected_out_text = f"{quoted_out / WAD:.9f}"
    min_out_text = f"{min_out / WAD:.9f}"
    max_gas_eth = max_gas_cost / WAD
    proposal = {
        "network": "Base Sepolia",
        "chain_id": CHAIN_ID,
        "wallet": recipient,
        "router": router_address,
        "router_name": router_name,
        "pair": pair_address,
        "pool": buy_pool,
        "token_in": usdc_address,
        "token_out": max_address,
        "amount_in": amount_in,
        "quoted_amount_out": quoted_out,
        "amount_out_min": min_out,
        "fee_bps_assumption": SWAP_FEE_BPS,
        "slippage_bps": MAX_SLIPPAGE_BPS,
        "gas_estimate": estimated_gas,
        "gas_limit": gas_limit,
        "gas_limit_cap": MAX_GAS_LIMIT,
        "gas_price_wei": gas_price,
        "max_gas_cost_wei": max_gas_cost,
    }
    phrase = (
        f"SEND {amount_text} tUSDC TO {recipient} VIA {router_address} "
        f"MIN_OUT_BASE_UNITS {min_out}"
    )
    print("PROPOSED SINGLE TEST SWAP - NOT AN ARBITRAGE")
    print(f"Network: Base Sepolia (chain ID {CHAIN_ID})")
    print(f"Bot wallet / recipient: {recipient}")
    print(f"Router: {router_address} ({router_name})")
    print(f"Pair: {pair_address} ({buy_pool}); tUSDC -> MAX")
    print(f"Amount in: {amount_text} tUSDC")
    print(f"Expected output (0.30% fee model): {expected_out_text} MAX")
    print(f"Modeled fee + price impact: {modeled_impact_bps} bps")
    print(f"amountOutMin ({MAX_SLIPPAGE_BPS} bps below quote): {min_out_text} MAX")
    print(f"Gas: estimate {estimated_gas}; limit {gas_limit}; price {gas_price} wei")
    print(f"Configured gas limit cap: {MAX_GAS_LIMIT}")
    print(
        f"Maximum native gas cost at quoted gas price: "
        f"{max_gas_eth:.12f} ETH ({max_gas_cost} wei)"
    )
    print("This swap leaves the wallet holding MAX; no arbitrage/profit is claimed.")
    answer = input(f'To authorize this exact swap, type: {phrase}\n> ').strip()
    if answer != phrase:
        raise RuntimeError("Transaction not approved; no transaction was sent")

    # Revalidate the values that can change while the user reviews the proposal.
    if w3.eth.chain_id != CHAIN_ID or w3.eth.gas_price != gas_price:
        raise RuntimeError("Chain or gas price changed after approval; request a fresh proposal")
    current_pool = _read_pool(buy_pool)
    current_quote = amount_out(amount_in, current_pool["usdc"], current_pool["max"])
    if current_quote < min_out:
        raise RuntimeError("Pool quote moved below amountOutMin after approval; execution refused")
    if (usdc.functions.balanceOf(recipient).call() < amount_in
            or usdc.functions.allowance(recipient, router_address).call() < amount_in
            or w3.eth.get_balance(recipient) < max_gas_cost):
        raise RuntimeError("Wallet balance or allowance changed after approval; execution refused")

    before_usdc = usdc.functions.balanceOf(recipient).call()
    before_max = max_token.functions.balanceOf(recipient).call()
    global _send_attempted
    # Latch before invoking the sender. Even an ambiguous RPC/send error must
    # not cause the runner loop to blindly retry and potentially duplicate it.
    _send_attempted = True
    # Exactly one send attempt: chain.send() otherwise retries nonce-related
    # failures by default, which is inappropriate for this user-approved probe.
    receipt = send(swap_fn, gas=gas_limit, gas_price=gas_price, retries=1, key=key)
    if receipt.status != 1:
        raise RuntimeError("Transaction receipt failed; do not claim success")
    transaction = w3.eth.get_transaction(receipt.transactionHash)
    if (Web3.to_checksum_address(transaction["from"]) != recipient
            or Web3.to_checksum_address(transaction["to"]) != router_address):
        raise RuntimeError("Mined transaction sender/recipient mismatch; do not claim success")
    tx_input = transaction.get("input", "")
    if isinstance(tx_input, (bytes, bytearray)):
        tx_input = Web3.to_hex(tx_input)
    if (int(transaction.get("chainId", -1)) != CHAIN_ID
            or int(transaction.get("value", 0)) != 0
            or not isinstance(tx_input, str)
            or tx_input.lower() != swap_fn._encode_transaction_data().lower()):
        raise RuntimeError("Mined transaction chain/calldata/value mismatch; do not claim success")
    after_usdc = usdc.functions.balanceOf(recipient).call()
    after_max = max_token.functions.balanceOf(recipient).call()
    spent = before_usdc - after_usdc
    received = after_max - before_max
    if spent != amount_in or received < min_out:
        raise RuntimeError("Receipt succeeded but balance deltas failed verification")
    return {
        "proposal": proposal,
        "tx": receipt.transactionHash.hex(),
        "block": receipt.blockNumber,
        "wallet": recipient,
        "before_tUSDC": before_usdc,
        "after_tUSDC": after_usdc,
        "before_MAX": before_max,
        "after_MAX": after_max,
        "spent_tUSDC": spent,
        "received_MAX": received,
        "amountOutMin_MAX": min_out,
        "gas_used": receipt.gasUsed,
        "actual_gas_cost_wei": receipt.gasUsed * int(receipt.effectiveGasPrice),
        "line": "Single test swap verified; this is not an arbitrage result.",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=NAME)
    parser.add_argument(
        "--test-swap-once", action="store_true",
        help="propose one guarded tUSDC -> MAX execution test; never loops",
    )
    args = parser.parse_args()
    signal = scan()
    print(signal["line"])
    if args.test_swap_once:
        print(fire(signal))
