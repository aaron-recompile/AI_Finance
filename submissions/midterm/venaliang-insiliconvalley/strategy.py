"""Vena Band Rebalancer: constant-mix inventory, rather than round-trip arbitrage.

Run this file for one read-only scan; --live allows at most one rebalance.
The original course orchestrator can also import NAME, scan() and fire(view).
decide(view) is pure and uses integer token units (18 decimals in this lab).
"""
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

NAME = "vena-band-rebalancer"
WALLET = "0x7AC5D1D870C0A1D0443740dD5214f58347945481"
WAD = 10**18
BPS = 10_000
TARGET, LOWER, UPPER = 2000, 1500, 2500
MAX_TRADE = 100 * WAD
MIN_TRADE = 5 * WAD
SLIPPAGE = 50
MAX_IMPACT = 100
COOLDOWN = 60
STATE = Path(os.environ.get("VENA_STATE", str(
    Path.home() / ".cache" / "ai-finance-midterm" / "vena-rebalancer-state.json")))


def _chain():
    # Work both in the student's submission folder and inside lab-bot.
    for parent in Path(__file__).resolve().parents:
        lab = parent / "week-03" / "code" / "lab-bot"
        if (lab / "chain.py").exists():
            sys.path.insert(0, str(lab))
            break
    import chain
    return chain


def quote(amount, reserve_in, reserve_out):
    if min(amount, reserve_in, reserve_out) <= 0:
        return 0
    net = amount * 997
    return net * reserve_out // (reserve_in * 1000 + net)


def decide(view):
    """Rebalance only outside 15%-25% MAX; quote both pools at the actual size.

    view: {usd, max, pools: [{router, mx, usd}], block, last_trade, now}.
    Returns an actionable plan, or a reason to hold. No network or key access.
    """
    usd, mx = view["usd"], view["max"]
    hold = {"hit": False, "action": "hold"}
    if min(usd, mx) < 0:
        return {**hold, "line": "invalid negative wallet balance"}
    pools = view["pools"]
    if len(pools) != 2 or any(min(p["mx"], p["usd"]) <= 0 for p in pools):
        return {**hold, "line": "two funded pools required"}
    prices = [p["usd"] * WAD // p["mx"] for p in pools]
    if max(prices) * BPS > min(prices) * 12_000:
        return {**hold, "line": "pool prices disagree by >20%; hold"}
    # Reserve-weighted reference, used for sizing, never assumed to be executable.
    mark = sum(p["usd"] for p in pools) * WAD // sum(p["mx"] for p in pools)
    value = mx * mark // WAD
    nav = usd + value
    if nav <= 0:
        return {**hold, "line": "empty wallet"}
    weight = value * BPS // nav
    base = {"weight_bps": weight, "mark": mark, "block": view.get("block", 0)}
    if LOWER <= weight <= UPPER:
        return {**hold, **base, "line": f"MAX weight {weight/100:.2f}% within 15%-25%; hold"}
    if view.get("now", 0) - view.get("last_trade", 0) < COOLDOWN:
        return {**hold, **base, "line": "cooldown; hold"}
    buy = weight < LOWER
    delta = abs(nav * TARGET // BPS - value)
    # Keep at least 60% of pretrade NAV in tUSDC when buying.
    budget = min(delta, MAX_TRADE, max(0, usd - nav * 6000 // BPS)) if buy else min(delta, MAX_TRADE)
    if budget < MIN_TRADE:
        return {**hold, **base, "line": "rebalance below 5 tUSDC; hold"}
    amount = budget if buy else min(mx, budget * WAD // mark)
    candidates = []
    for pool in pools:
        rin, rout = (pool["usd"], pool["mx"]) if buy else (pool["mx"], pool["usd"])
        out = quote(amount, rin, rout)
        spot_out = amount * rout // rin
        # Includes the 0.3% fee; reject poor execution instead of using minOut=0.
        impact = (spot_out - out) * BPS // max(1, spot_out)
        if out > 0 and impact <= MAX_IMPACT:
            candidates.append((out, pool["router"], impact))
    if not candidates:
        return {**hold, **base, "line": "execution cost >1%; hold"}
    out, router, impact = max(candidates)
    return {**base, "hit": True, "action": "buy" if buy else "sell",
            "amount": amount, "expected_out": out,
            "min_out": max(1, out * (BPS - SLIPPAGE) // BPS), "router": router,
            "line": f"MAX {weight/100:.2f}% -> target 20% | {'BUY' if buy else 'SELL'} "
                    f"{amount/WAD:.6f} {'tUSDC' if buy else 'MAX'} via {router} | "
                    f"execution cost {impact/100:.3f}% | max 100 tUSDC per action"}


def _state():
    if not STATE.exists():
        return {"wallet": WALLET, "max_units": 0, "cost": 0, "realized": 0,
                "last_trade": 0, "pending": False, "trades": []}
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state["wallet"].lower() != WALLET.lower():
        raise RuntimeError("Ledger belongs to a different wallet")
    return state


def _save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE)


def read_view():
    c = _chain()
    c.w3.provider._request_kwargs["timeout"] = 20
    if c.w3.eth.chain_id != 84532:
        raise RuntimeError("Only Base Sepolia (84532) is permitted")
    me = c.w3.to_checksum_address(WALLET)
    block = c.w3.eth.block_number
    pools = []
    for pool_name, router in (("PoolA", "RouterA"), ("PoolB", "RouterB")):
        pool = c.at(c.ADDR[pool_name], "Pair")
        t0 = pool.functions.token0().call(block_identifier=block).lower()
        t1 = pool.functions.token1().call(block_identifier=block).lower()
        if {t0, t1} != {c.ADDR["MAX"].lower(), c.ADDR["tUSDC"].lower()}:
            raise RuntimeError("Unexpected pair tokens")
        r0, r1 = pool.functions.getReserves().call(block_identifier=block)
        mx, usd = (r0, r1) if t0 == c.ADDR["MAX"].lower() else (r1, r0)
        pools.append({"router": router, "mx": mx, "usd": usd})
    state = _state()
    return {"usd": c.erc20("tUSDC").functions.balanceOf(me).call(block_identifier=block),
            "max": c.erc20("MAX").functions.balanceOf(me).call(block_identifier=block),
            "pools": pools, "block": block, "now": int(time.time()),
            "last_trade": state["last_trade"], "pending": state["pending"]}


def scan():
    view = read_view()
    if view["pending"]:
        return {"hit": False, "line": "unresolved transaction journal; reconcile before trading"}
    result = decide(view)
    result["wallet"] = WALLET
    return result


@contextmanager
def _live_lock():
    """Use a persistent OS lock file to reject overlapping live runners."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with STATE.with_suffix(".lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def fire(previous):
    with _live_lock():
        return _fire(previous)


def _fire(previous):
    """One swap; exact allowance, positive minOut, receipt-derived accounting.

    Re-scan after approval. No fallback to the instructor key. If execution or
    accounting is uncertain, pending stays true and later scans stop trading.
    """
    c = _chain()
    key = os.environ.get("AGENT_KEY")
    if not key:
        raise RuntimeError("Set AGENT_KEY locally; never send it in chat")
    if c.acct_of(key).address.lower() != WALLET.lower():
        raise RuntimeError("Signing key does not match the assignment wallet")
    if c.w3.eth.chain_id != 84532:
        raise RuntimeError("Wrong chain")
    state = _state()
    if state["pending"]:
        raise RuntimeError("Reconcile the pending journal first")
    view = read_view()
    plan = decide(view)
    if not plan["hit"]:
        return {"profit": 0, "note": plan["line"]}
    if state["max_units"] != view["max"]:
        raise RuntimeError("MAX balance differs from cost ledger; reconcile external activity")
    if not previous.get("hit") or any(plan[k] != previous.get(k) for k in ("action", "router")):
        return {"profit": 0, "note": "direction/route changed; wait for next scan"}
    token_in, token_out = ("tUSDC", "MAX") if plan["action"] == "buy" else ("MAX", "tUSDC")
    me = c.w3.to_checksum_address(WALLET)
    spender = c.w3.to_checksum_address(c.ADDR[plan["router"]])
    # Budget a swap plus an approval, while preserving a gas reserve.
    if c.w3.eth.get_balance(me) < c.w3.eth.gas_price * 1_000_000 + 10**14:
        raise RuntimeError("Insufficient test ETH gas reserve")
    allowance = c.erc20(token_in).functions.allowance(me, spender).call()
    approval_tx = None
    state["pending"] = True
    state["intent"] = {"action": plan["action"], "router": plan["router"],
                       "amount": plan["amount"], "created_at": int(time.time())}
    _save(state)
    if allowance < plan["amount"]:
        approval = c.send(c.erc20(token_in).functions.approve(spender, plan["amount"]),
                          gas=120_000, retries=1, key=key)
        approval_tx = c.w3.to_hex(approval.transactionHash)
        state["intent"]["approval_tx"] = approval_tx
        _save(state)
    fresh_view = read_view()
    fresh = decide(fresh_view)
    if (not fresh["hit"] or any(fresh[k] != plan[k] for k in ("action", "router"))
            or fresh_view["max"] != view["max"] or fresh_view["usd"] != view["usd"]
            or fresh["amount"] > plan["amount"]):
        state["pending"] = False
        _save(state)
        return {"profit": 0, "note": "market or balances changed after approval; no swap"}
    fn = c.at(spender, "Router").functions.swapExactTokensForTokens(
        fresh["amount"], fresh["min_out"], c.ADDR[token_in], c.ADDR[token_out], me)
    # Simulate on the RPC immediately before signing.
    fn.call({"from": me})
    rcpt = c.send(fn, gas=800_000, retries=1, key=key)
    tx = c.w3.to_hex(rcpt.transactionHash)
    state["intent"]["swap_tx"] = tx
    _save(state)
    # Derive the acquired amount from this transaction's Transfer logs, not laggy balances.
    transfer = c.w3.keccak(text="Transfer(address,address,uint256)")
    received = sum(int.from_bytes(log["data"], "big") for log in rcpt.logs
                   if log["address"].lower() == c.ADDR[token_out].lower()
                   and len(log["topics"]) == 3 and log["topics"][0] == transfer
                   and log["topics"][2][-20:].hex().lower() == WALLET[2:].lower())
    if received < fresh["min_out"]:
        raise RuntimeError(f"Swap confirmed ({tx}); output accounting needs reconciliation")
    realized = 0
    if fresh["action"] == "buy":
        state["max_units"] += received
        state["cost"] += fresh["amount"]
    else:
        cost_sold = state["cost"] * fresh["amount"] // state["max_units"]
        state["max_units"] -= fresh["amount"]
        state["cost"] -= cost_sold
        realized = received - cost_sold
        state["realized"] += realized
    record = {"tx": tx, "approval_tx": approval_tx, "action": fresh["action"],
              "router": fresh["router"], "amount_in": fresh["amount"], "amount_out": received,
              "realized_tusdc": realized / WAD, "block": rcpt.blockNumber,
              "swap_gas_eth": str(c.w3.from_wei(rcpt.gasUsed * rcpt.effectiveGasPrice, "ether"))}
    state["trades"].append(record)
    state["last_trade"] = int(time.time())
    state["pending"] = False
    _save(state)
    return {"tx": tx, "profit": realized / WAD,
            "note": "realized tUSDC vs weighted acquisition cost; ETH gas excluded", **record}


if __name__ == "__main__":
    result = scan()
    print(json.dumps(result, indent=2))
    if "--live" in sys.argv and result["hit"]:
        print(json.dumps(fire(result), indent=2))
