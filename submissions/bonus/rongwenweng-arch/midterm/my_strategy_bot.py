"""my_strategy_bot.py — CrossFamilyRouter, on-chain adapter (Track B mid-term, Rongwen Weng).

The strategy lives in strategy.py as decide(view). This file only does the plumbing:

    scan()  read all 4 venues + my balance into a `view`, ask decide(view).
    fire()  leg 1: buy MAX on the venue decide() picked.
            leg 2: RE-ROUTE — re-read the chain and sell on whichever venue pays the
            most right now (the gap may have moved between my two transactions).

  Every round uses my whole tUSDC balance, so profit compounds into the next round.

RUN (copy this file AND strategy.py into week-03/code/lab-bot/)
    python run.py my_strategy_bot              # DRY-RUN (scan only, safe)
    python run.py my_strategy_bot --live       # LIVE (needs AGENT_KEY)
  Dry-run works without a key: set AGENT_ADDR=0x... to size against a real wallet.
    python my_strategy_bot.py --unwind 2.5     # sell 2.5 stranded MAX on the best venue
"""
import os
import sys
import time
from decimal import Decimal
from web3 import Web3
from chain import ADDR, at, erc20, send, ensure_allowance, acct_of
from strategy import NAME, WAD, quote, decide, best_exit

KEY = os.environ.get("AGENT_KEY")            # my wallet's key — only needed for --live
ME = acct_of(KEY).address if KEY else os.environ.get("AGENT_ADDR")
if ME:
    ME = Web3.to_checksum_address(ME.lower())

SLIPPAGE_BPS = 100                           # router legs revert if I get <99% of my quote
DRY_SIZE = 1_000 * WAD                       # sizing cap when no wallet is known (dry-run)

# name -> (kind, pool address key, router address key or None)
VENUES = {
    "CHEAP": ("amm", "CHEAP", None),
    "DEAR":  ("amm", "DEAR", None),
    "PoolA": ("pair", "PoolA", "RouterA"),
    "PoolB": ("pair", "PoolB", "RouterB"),
}
_MAX_IS_T0 = {}                              # cache: is MAX token0 of this pool?


def _max_is_token0(v):
    if v not in _MAX_IS_T0:
        kind, pool, _ = VENUES[v]
        c = at(ADDR[pool], "SimpleAMM" if kind == "amm" else "Pair")
        _MAX_IS_T0[v] = c.functions.token0().call().lower() == ADDR["MAX"].lower()
    return _MAX_IS_T0[v]


def _reserves(v):
    """(MAX reserve, tUSDC reserve) of a venue, whichever way round the pool stores them."""
    kind, pool, _ = VENUES[v]
    if kind == "amm":
        c = at(ADDR[pool], "SimpleAMM")
        r0, r1 = c.functions.reserve0().call(), c.functions.reserve1().call()
    else:
        r0, r1 = at(ADDR[pool], "Pair").functions.getReserves().call()
    return (r0, r1) if _max_is_token0(v) else (r1, r0)


def _view():
    """Snapshot the market for decide(): every venue's reserves + my tUSDC balance."""
    usdc = erc20("tUSDC").functions.balanceOf(ME).call() if ME else DRY_SIZE
    return {"reserves": {v: _reserves(v) for v in VENUES}, "usdc": usdc}


def scan():
    return decide(_view())


def _buy_max(v, usd_in, min_out):
    kind, pool, router = VENUES[v]
    if kind == "amm":
        ensure_allowance("tUSDC", ADDR[pool], key=KEY)
        c = at(ADDR[pool], "SimpleAMM")       # MAX is token0 here, so tUSDC -> MAX is 1For0
        fn = c.functions.swap1For0(usd_in) if _max_is_token0(v) else c.functions.swap0For1(usd_in)
        return send(fn, key=KEY)
    ensure_allowance("tUSDC", ADDR[router], key=KEY)
    return send(at(ADDR[router], "Router").functions.swapExactTokensForTokens(
        usd_in, min_out, ADDR["tUSDC"], ADDR["MAX"], ME), key=KEY)


def _sell_max(v, max_in, min_out):
    kind, pool, router = VENUES[v]
    if kind == "amm":
        ensure_allowance("MAX", ADDR[pool], key=KEY)
        c = at(ADDR[pool], "SimpleAMM")
        fn = c.functions.swap0For1(max_in) if _max_is_token0(v) else c.functions.swap1For0(max_in)
        return send(fn, key=KEY)
    ensure_allowance("MAX", ADDR[router], key=KEY)
    return send(at(ADDR[router], "Router").functions.swapExactTokensForTokens(
        max_in, min_out, ADDR["MAX"], ADDR["tUSDC"], ME), key=KEY)


def _wait_change(token, before, tries=12):
    """Public RPCs can lag a block behind my own tx — poll until the balance moves."""
    now = before
    for _ in range(tries):
        now = token.functions.balanceOf(ME).call()
        if now != before:
            break
        time.sleep(0.5)
    return now


def fire(s):
    if not KEY:
        raise RuntimeError("set AGENT_KEY to go --live")
    usdc, mx = erc20("tUSDC"), erc20("MAX")
    u_before = usdc.functions.balanceOf(ME).call()
    m_before = mx.functions.balanceOf(ME).call()
    D = min(s["size_wei"], u_before)

    # leg 1: buy MAX on the cheap venue (re-quoted now, with a slippage floor)
    m1, u1 = _reserves(s["buy"])
    floor = quote(D, u1, m1) * (10000 - SLIPPAGE_BPS) // 10000
    r1 = _buy_max(s["buy"], D, floor)
    got_max = _wait_change(mx, m_before) - m_before
    if got_max <= 0:
        raise RuntimeError("buy landed but MAX balance still stale — not selling")
    u_mid = _wait_change(usdc, u_before)

    # leg 2: re-route — sell on whichever venue pays the most at THIS moment
    sell_v, q = best_exit(_view(), got_max)
    r2 = _sell_max(sell_v, got_max, q * (10000 - SLIPPAGE_BPS) // 10000)
    u_final = _wait_change(usdc, u_mid)
    return {"tx": r2.transactionHash.hex(), "buy_tx": r1.transactionHash.hex(),
            "profit": (u_final - u_before) / WAD,
            "note": f"bought {got_max/WAD:.4f} MAX on {s['buy']}, sold on {sell_v}"}


def unwind(max_amount):
    """Sell a stranded leg: MAX that leg 1 bought but leg 2 never sold (bot stopped mid-round)."""
    if not KEY:
        raise RuntimeError("set AGENT_KEY to unwind")
    usdc = erc20("tUSDC")
    u_before = usdc.functions.balanceOf(ME).call()
    sell_v, q = best_exit(_view(), max_amount)
    r = _sell_max(sell_v, max_amount, q * (10000 - SLIPPAGE_BPS) // 10000)
    u_final = _wait_change(usdc, u_before)
    return {"tx": r.transactionHash.hex(), "received": (u_final - u_before) / WAD,
            "note": f"sold {max_amount/WAD:.4f} MAX on {sell_v}"}


if __name__ == "__main__":
    if "--unwind" in sys.argv:               # python my_strategy_bot.py --unwind 2.1312
        amount = Decimal(sys.argv[sys.argv.index("--unwind") + 1])
        print("  unwinding...", unwind(int(amount * WAD)))
        sys.exit()
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
