"""my_strategy_bot.py — NexusRouter On-Chain Adapter (Track B, claine-cstu).

Connects strategy.py to the Base Sepolia testnet arena.

INTERFACE:
    NAME            : str
    scan() -> dict  : read live state, return decision dict with 'hit' and 'line'
    fire(s) -> dict : execute leg 1 -> re-route -> leg 2; or execute safety unwind / auto-mint

CONFIGURATION:
    Reads private key from:
      1. AGENT_KEY or PRIVATE_KEY environment variables, or
      2. variables.txt in the workspace root.
"""
import os
import sys
import time
from web3 import Web3

# Support importing chain.py whether running from lab-bot/ or submissions/
try:
    from chain import ADDR, at, erc20, send, ensure_allowance, acct_of, w3
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "week-03", "code", "lab-bot")))
    from chain import ADDR, at, erc20, send, ensure_allowance, acct_of, w3

from strategy import NAME, WAD, quote, decide, best_exit


def _load_key() -> str | None:
    k = os.environ.get("AGENT_KEY") or os.environ.get("PRIVATE_KEY")
    if k:
        return k.strip()
    # Check variables.txt in root
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "variables.txt")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "variables.txt")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "variables.txt")),
        "variables.txt",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                for line in open(path):
                    if "PRIVATE KEY" in line:
                        return line.split(":", 1)[1].strip()
            except Exception:
                pass
    return None


KEY = _load_key()
ME = acct_of(KEY).address if KEY else os.environ.get("AGENT_ADDR")
if ME:
    ME = Web3.to_checksum_address(ME.lower())

SLIPPAGE_BPS = 100                 # 1% slippage floor on router legs
DRY_SIZE = 1_000 * WAD             # Default balance simulation for dry-run scans
MINT_ABI = [{"name": "mint", "type": "function", "inputs": [{"type": "address"}, {"type": "uint256"}], "outputs": []}]

# Venue registry: venue_name -> (type, pool_key, router_key_or_none)
VENUES = {
    "CHEAP": ("amm", "CHEAP", None),
    "DEAR":  ("amm", "DEAR", None),
    "PoolA": ("pair", "PoolA", "RouterA"),
    "PoolB": ("pair", "PoolB", "RouterB"),
}

_MAX_IS_T0 = {}


def _max_is_token0(v: str) -> bool:
    """Check and cache whether MAX is token0 of venue v."""
    if v not in _MAX_IS_T0:
        kind, pool, _ = VENUES[v]
        c = at(ADDR[pool], "SimpleAMM" if kind == "amm" else "Pair")
        _MAX_IS_T0[v] = c.functions.token0().call().lower() == ADDR["MAX"].lower()
    return _MAX_IS_T0[v]


def _reserves(v: str) -> tuple[int, int]:
    """Return (MAX reserve, tUSDC reserve) in wei."""
    kind, pool, _ = VENUES[v]
    if kind == "amm":
        c = at(ADDR[pool], "SimpleAMM")
        r0, r1 = c.functions.reserve0().call(), c.functions.reserve1().call()
    else:
        r0, r1 = at(ADDR[pool], "Pair").functions.getReserves().call()
    return (r0, r1) if _max_is_token0(v) else (r1, r0)


def build_view() -> dict:
    """Query live blockchain state for reserves and wallet balances."""
    reserves = {v: _reserves(v) for v in VENUES}
    if ME:
        usdc_bal = erc20("tUSDC").functions.balanceOf(ME).call()
        max_bal = erc20("MAX").functions.balanceOf(ME).call()
        eth_bal = w3.eth.get_balance(ME)
    else:
        usdc_bal = DRY_SIZE
        max_bal = 0
        eth_bal = 0
    return {
        "reserves": reserves,
        "usdc": usdc_bal,
        "max": max_bal,
        "eth": eth_bal,
    }


def scan() -> dict:
    """Interface method required by orchestrator.py and run.py."""
    view = build_view()
    eth_bal = view.get("eth", 0)
    usdc_bal = view.get("usdc", 0)
    max_bal = view.get("max", 0)

    # 1. If wallet has gas ETH but zero trading tokens, trigger auto-mint
    if ME and eth_bal >= int(0.0001 * WAD) and usdc_bal == 0 and max_bal == 0:
        return {
            "action": "mint",
            "hit": True,
            "line": f"Wallet {ME[:8]}… has {eth_bal/WAD:.5f} ETH but 0 tUSDC => Auto-minting 1,000 tUSDC from public course faucet",
        }

    # 2. If wallet has zero gas ETH
    if ME and eth_bal == 0 and (usdc_bal == 0 or max_bal == 0):
        decision = decide(view)
        decision["line"] += f" | NOTE: Wallet has 0.000 ETH gas. Send test ETH to {ME} to execute."
        return decision

    # 3. Standard strategy evaluation (trade / unwind / hold)
    return decide(view)


def _wait_balance_increase(token_symbol: str, target_addr: str, previous_balance: int, max_retries: int = 15) -> int:
    """Poll ERC20 balance until a confirmed increase is indexed by the RPC node."""
    token = erc20(token_symbol)
    for _ in range(max_retries):
        current_balance = token.functions.balanceOf(target_addr).call()
        if current_balance > previous_balance:
            return current_balance - previous_balance
        time.sleep(0.6)
    return max(0, token.functions.balanceOf(target_addr).call() - previous_balance)


def _buy_max(venue: str, usdc_in: int, min_max_out: int):
    """Execute Leg 1: swap tUSDC for MAX on specified venue."""
    kind, pool, router = VENUES[venue]
    if kind == "amm":
        ensure_allowance("tUSDC", ADDR[pool], key=KEY)
        c = at(ADDR[pool], "SimpleAMM")
        fn = c.functions.swap1For0(usdc_in) if _max_is_token0(venue) else c.functions.swap0For1(usdc_in)
        return send(fn, key=KEY)
    else:
        ensure_allowance("tUSDC", ADDR[router], key=KEY)
        r = at(ADDR[router], "Router")
        return send(r.functions.swapExactTokensForTokens(
            usdc_in, min_max_out, ADDR["tUSDC"], ADDR["MAX"], ME), key=KEY)


def _sell_max(venue: str, max_in: int, min_usdc_out: int):
    """Execute Leg 2: swap MAX for tUSDC on specified venue."""
    kind, pool, router = VENUES[venue]
    if kind == "amm":
        ensure_allowance("MAX", ADDR[pool], key=KEY)
        c = at(ADDR[pool], "SimpleAMM")
        fn = c.functions.swap0For1(max_in) if _max_is_token0(venue) else c.functions.swap1For0(max_in)
        return send(fn, key=KEY)
    else:
        ensure_allowance("MAX", ADDR[router], key=KEY)
        r = at(ADDR[router], "Router")
        return send(r.functions.swapExactTokensForTokens(
            max_in, min_usdc_out, ADDR["MAX"], ADDR["tUSDC"], ME), key=KEY)


def fire(s: dict) -> dict:
    """Execute the trading action chosen by scan(). Requires KEY in live mode."""
    if not KEY:
        raise RuntimeError("fire() requires private key in variables.txt or AGENT_KEY in environment")

    action = s.get("action")
    usdc_erc = erc20("tUSDC")
    max_erc = erc20("MAX")

    # CASE 0: AUTO-MINT ACTION (Free course faucet)
    if action == "mint":
        c = w3.eth.contract(address=ADDR["tUSDC"], abi=MINT_ABI)
        mint_amt = 1000 * WAD
        u_before = usdc_erc.functions.balanceOf(ME).call()
        rcpt = send(c.functions.mint(ME, mint_amt), key=KEY)
        _wait_balance_increase("tUSDC", ME, u_before)
        return {
            "action": "mint",
            "tx": rcpt.transactionHash.hex(),
            "minted_tUSDC": 1000.0,
            "note": "Minted 1,000 tUSDC from open course mint. Next tick will trade.",
        }

    # CASE 1: UNWIND ACTION (Safety Shield)
    if action == "unwind":
        max_held = max_erc.functions.balanceOf(ME).call()
        if max_held == 0:
            return {"action": "unwind", "profit": 0.0, "note": "no MAX to unwind"}

        live_view = build_view()
        exit_v, est_usdc = best_exit(live_view, max_held)
        min_out = int(est_usdc * (10000 - SLIPPAGE_BPS) // 10000)

        u_before = usdc_erc.functions.balanceOf(ME).call()
        rcpt = _sell_max(exit_v, max_held, min_out)
        recovered = _wait_balance_increase("tUSDC", ME, u_before)
        return {
            "action": "unwind",
            "tx": rcpt.transactionHash.hex(),
            "profit": recovered / WAD,
            "recovered_tUSDC": recovered / WAD,
            "sold_MAX": max_held / WAD,
            "venue": exit_v,
        }

    # CASE 2: REGULAR TWO-LEG ARBITRAGE ACTION
    buy_v = s["buy"]
    size_usdc = s["size_wei"]

    r_buy_m, r_buy_u = _reserves(buy_v)
    exp_max_out = quote(size_usdc, r_buy_u, r_buy_m)
    min_max_out = int(exp_max_out * (10000 - SLIPPAGE_BPS) // 10000)

    u_before = usdc_erc.functions.balanceOf(ME).call()
    m_before = max_erc.functions.balanceOf(ME).call()

    # LEG 1: Buy MAX
    rcpt1 = _buy_max(buy_v, size_usdc, min_max_out)
    actual_max_bought = _wait_balance_increase("MAX", ME, m_before)
    if actual_max_bought <= 0:
        actual_max_bought = max_erc.functions.balanceOf(ME).call() - m_before

    if actual_max_bought <= 0:
        raise RuntimeError(f"Leg 1 succeeded ({rcpt1.transactionHash.hex()}) but no MAX was received")

    # LEG 2 RE-ROUTE: Re-read live chain to guarantee optimal exit venue
    live_view = build_view()
    sell_v, est_usdc_out = best_exit(live_view, actual_max_bought)
    min_usdc_out = int(est_usdc_out * (10000 - SLIPPAGE_BPS) // 10000)

    # LEG 2: Sell MAX on best venue
    rcpt2 = _sell_max(sell_v, actual_max_bought, min_usdc_out)
    _wait_balance_increase("tUSDC", ME, u_before)

    u_after = usdc_erc.functions.balanceOf(ME).call()
    net_profit = (u_after - u_before) / WAD

    return {
        "action": "trade",
        "tx": rcpt2.transactionHash.hex(),
        "leg1_tx": rcpt1.transactionHash.hex(),
        "leg2_tx": rcpt2.transactionHash.hex(),
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "size_spent_tUSDC": size_usdc / WAD,
        "max_traded": actual_max_bought / WAD,
        "profit": round(net_profit, 2),
        "note": f"Buy {buy_v} -> Sell {sell_v} => net {net_profit:+,.2f} tUSDC",
    }


def mock_trade(size_usdc: float = 1000.0) -> dict:
    """Simulates an on-chain trade against live Base Sepolia reserves without requiring gas,
    updates state.json for dashboard.html, and appends to pnl.log."""
    import json
    view = build_view()
    reserves = view["reserves"]
    d_in = int(size_usdc * WAD)

    best_pair = None
    best_p = 0
    for b in reserves:
        for s in reserves:
            if b == s:
                continue
            (m1, u1), (m2, u2) = reserves[b], reserves[s]
            max_out = quote(d_in, u1, m1)
            u_out = quote(max_out, m2, u2)
            p = u_out - d_in
            if p > best_p:
                best_p = p
                best_pair = (b, s, max_out, u_out)

    if not best_pair:
        return {"status": "no profitable route", "profit": 0.0}

    buy_v, sell_v, max_acquired, u_out = best_pair
    net_profit = (u_out - d_in) / WAD
    tx_hash = f"0xmock{int(time.time()):x}{Web3.keccak(text=f'{buy_v}{sell_v}{time.time()}').hex()[:32]}"

    res = {
        "action": "trade (mock/simulated)",
        "tx": tx_hash,
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "size_spent_tUSDC": size_usdc,
        "max_traded": round(max_acquired / WAD, 4),
        "usdc_returned": round(u_out / WAD, 2),
        "profit": round(net_profit, 2),
        "roi_pct": round(net_profit / size_usdc * 100, 2),
        "note": f"Simulated execution against live Base Sepolia reserves: Buy {buy_v} -> Sell {sell_v}",
    }

    # Update state.json and pnl.log for dashboard.html
    here = os.path.dirname(os.path.abspath(__file__))
    state_file = os.path.join(here, "state.json")
    pnl_file = os.path.join(here, "pnl.log")

    st = {
        "updated": time.strftime("%H:%M:%S"),
        "tick": 1,
        "mode": "SIMULATED / MOCK",
        "bots": [{
            "name": NAME,
            "hit": True,
            "line": f"MOCK TRADE: Buy {buy_v} -> Sell {sell_v} | spent {size_usdc:,.0f} tUSDC | profit {net_profit:+,.2f} tUSDC",
            "pnl": round(net_profit, 2),
            "fires": 1,
            "last_tx": tx_hash,
            "fired": True,
        }],
        "total_pnl": round(net_profit, 2),
    }
    json.dump(st, open(state_file, "w"), indent=2)

    with open(pnl_file, "a") as f:
        f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "bot": NAME, "tx": tx_hash, "profit": round(net_profit, 2), "note": res["note"]}) + "\n")

    return res


if __name__ == "__main__":
    if "--mock" in sys.argv:
        print("=== Executing Mock Trade against Live Base Sepolia Reserves ===")
        res = mock_trade(1000.0)
        for k, v in res.items():
            print(f"  {k}: {v}")
        print("\nDashboard state updated! You can now open dashboard.html in your browser to view the leaderboard.")
        sys.exit(0)

    if "--unwind" in sys.argv:
        idx = sys.argv.index("--unwind")
        amt = float(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None
        live_v = build_view()
        max_held = int(amt * WAD) if amt else erc20("MAX").functions.balanceOf(ME).call()
        v, exp_u = best_exit(live_v, max_held)
        print(f"Unwinding {max_held/WAD:.4f} MAX on {v} for est {exp_u/WAD:,.2f} tUSDC...")
        if KEY:
            res = fire({"action": "unwind", "venue": v})
            print("Unwind complete:", res)
        else:
            print("Dry-run only: set AGENT_KEY to execute live unwind.")
        sys.exit(0)

    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s.get('hit') else 'skip'}")
    if s.get("hit") and "--live" in sys.argv:
        print("Executing live on-chain action...")
        res = fire(s)
        print("Action complete:", res)

