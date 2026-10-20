"""my_strategy_bot.py — ConsensusMaker, the on-chain adapter (Track B mid-term).

The strategy itself lives in fair_value.py (pure math, offline-testable). This file
only reads the chain into a `view`, asks `decide(view)` what to do, and sends the
one transaction it answers with — signed by MY wallet (AGENT_KEY).

HOW TO RUN  (from inside week-03/code/lab-bot/, with fair_value.py beside this file)
    export AGENT_KEY=0x...                               # never commit
    python run.py my_strategy_bot                        # DRY-RUN
    python run.py my_strategy_bot --live                 # LIVE, one bot
    python orchestrator.py --only my_strategy_bot --live # LIVE + writes state.json
                                                         #   -> dashboard.html leaderboard
    python my_strategy_bot.py balances                   # just print my balances
"""
import os, sys, time
from chain import ADDR, at, erc20, send, ensure_allowance, acct_of
from fair_value import NAME, WAD, FEE_BPS, quote, decide  # noqa: F401 (NAME re-exported)

KEY = os.environ["AGENT_KEY"]
ME = acct_of(KEY).address

# The four MAX/tUSDC venues. "pair" venues are Uniswap-v2 style and trade through a
# router with a min-out; "amm" venues are the flash-demo SimpleAMMs, traded directly.
VENUES = {
    "PoolA": {"kind": "pair", "pool": "PoolA", "router": "RouterA"},
    "PoolB": {"kind": "pair", "pool": "PoolB", "router": "RouterB"},
    "CHEAP": {"kind": "amm",  "pool": "CHEAP"},
    "DEAR":  {"kind": "amm",  "pool": "DEAR"},
}
SLIPPAGE_BPS = 100          # router legs: min-out 1% below quote
AMM_DRIFT_BPS = 100         # SimpleAMM legs: abort if price moved >1% since scan
_T0 = {}


def _max_is_token0(v):
    key = v["pool"]
    if key not in _T0:
        abi = "Pair" if v["kind"] == "pair" else "SimpleAMM"
        _T0[key] = at(ADDR[key], abi).functions.token0().call().lower() == ADDR["MAX"].lower()
    return _T0[key]


def _reserves(v):
    """(MAX reserve, tUSDC reserve) in wei, whichever side each token sits on."""
    if v["kind"] == "pair":
        r0, r1 = at(ADDR[v["pool"]], "Pair").functions.getReserves().call()
    else:
        c = at(ADDR[v["pool"]], "SimpleAMM")
        r0, r1 = c.functions.reserve0().call(), c.functions.reserve1().call()
    return (r0, r1) if _max_is_token0(v) else (r1, r0)


def _view():
    return {"venues": {n: _reserves(v) for n, v in VENUES.items()},
            "usdc": erc20("tUSDC").functions.balanceOf(ME).call(),
            "max": erc20("MAX").functions.balanceOf(ME).call()}


def scan():
    return decide(_view())


def _hx(h):
    """0x-prefixed hex for a tx hash (hexbytes >= 1.0 drops the prefix from .hex())."""
    s = h.hex()
    return s if s.startswith("0x") else "0x" + s


def _wait_change(token, before, tries=12):
    """Public RPC can lag a node behind right after a tx; poll until the balance moves."""
    for _ in range(tries):
        now = erc20(token).functions.balanceOf(ME).call()
        if now != before:
            return now
        time.sleep(0.5)
    return erc20(token).functions.balanceOf(ME).call()


def _swap(v, side, amount, min_out):
    """One leg on one venue. BUY = tUSDC -> MAX, SELL = MAX -> tUSDC."""
    tok_in, tok_out = ("tUSDC", "MAX") if side == "BUY" else ("MAX", "tUSDC")
    if v["kind"] == "pair":
        ensure_allowance(tok_in, ADDR[v["router"]], key=KEY)
        r = at(ADDR[v["router"]], "Router")
        return send(r.functions.swapExactTokensForTokens(
            amount, min_out, ADDR[tok_in], ADDR[tok_out], ME), key=KEY)
    # SimpleAMM: swap1For0 = give token1 get token0, swap0For1 = the reverse
    ensure_allowance(tok_in, ADDR[v["pool"]], key=KEY)
    c = at(ADDR[v["pool"]], "SimpleAMM")
    max0 = _max_is_token0(v)
    give_max = side == "SELL"
    fn = c.functions.swap0For1 if (give_max == max0) else c.functions.swap1For0
    return send(fn(amount), key=KEY)


def fire(s):
    v, side, size = VENUES[s["venue"]], s["side"], s["size"]
    m, u = _reserves(v)                                   # fresh read right before sending
    if side == "BUY":
        expected = quote(size, u, m)
        px_now = u / m
        if px_now > (s["fair"] * (1 + s["devs"][s["venue"]])) * (1 + AMM_DRIFT_BPS / 10000):
            return {"tx": None, "profit": 0.0, "note": "venue moved away since scan — skipped"}
        before = erc20("MAX").functions.balanceOf(ME).call()
        rcpt = _swap(v, "BUY", size, expected * (10000 - SLIPPAGE_BPS) // 10000)
        got = _wait_change("MAX", before) - before
        edge = got * s["fair"] * (10000 - FEE_BPS) / 10000 - size
        return {"tx": _hx(rcpt.transactionHash), "profit": edge / WAD,
                "note": f"bought {got/WAD:.4f} MAX on {s['venue']} for {size/WAD:,.2f} tUSDC "
                        f"(avg {size/got:.2f} vs fair {s['fair']:.2f})"}
    else:
        expected = quote(size, m, u)
        px_now = u / m
        if px_now < (s["fair"] * (1 + s["devs"][s["venue"]])) * (1 - AMM_DRIFT_BPS / 10000):
            return {"tx": None, "profit": 0.0, "note": "venue moved away since scan — skipped"}
        before = erc20("tUSDC").functions.balanceOf(ME).call()
        rcpt = _swap(v, "SELL", size, expected * (10000 - SLIPPAGE_BPS) // 10000)
        got = _wait_change("tUSDC", before) - before
        edge = got - size * s["fair"] * (10000 + FEE_BPS) / 10000
        return {"tx": _hx(rcpt.transactionHash), "profit": edge / WAD,
                "note": f"sold {size/WAD:.4f} MAX on {s['venue']} for {got/WAD:,.2f} tUSDC "
                        f"(avg {got/size:.2f} vs fair {s['fair']:.2f})"}


if __name__ == "__main__":
    if "balances" in sys.argv:
        vw = _view()
        print(f"{ME}  tUSDC {vw['usdc']/WAD:,.2f}  MAX {vw['max']/WAD:.4f}")
        sys.exit()
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
