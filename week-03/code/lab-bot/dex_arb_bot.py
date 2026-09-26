"""dex_arb_bot.py — DexArbBot (real two-DEX arbitrage, own capital).

The automated version of arb.html: watch MAX/tUSDC on DEX-A vs DEX-B. When a
human skews one pool and a gap opens, buy MAX on the cheaper DEX and sell it on
the dearer DEX with the bot's own tUSDC. Profit = tUSDC out - tUSDC in.
"""
import sys, time
from chain import at, contract, ADDR, erc20, send, ensure_allowance, acct_of, load_bot_key

NAME = "dex-arb"
KEY = load_bot_key(NAME)          # this bot's own wallet
ME = acct_of(KEY).address
WAD = 10 ** 18
SWAP_BPS = 30
MIN_PROFIT = 1 * WAD
_TOKEN0 = {}  # cache pool -> token0


def _token0(pool):
    if pool not in _TOKEN0:
        _TOKEN0[pool] = at(ADDR[pool], "Pair").functions.token0().call().lower()
    return _TOKEN0[pool]


def _mx_usd(pool):
    """Return (MAX reserve, tUSDC reserve) for a MAX/tUSDC pool."""
    r0, r1 = at(ADDR[pool], "Pair").functions.getReserves().call()
    return (r0, r1) if _token0(pool) == ADDR["MAX"].lower() else (r1, r0)


def _out(amount_in, r_in, r_out):
    a = amount_in * (10000 - SWAP_BPS)
    return a * r_out // (r_in * 10000 + a)


def _profit(D, cheap, dear):
    mc, uc = cheap   # cheap: buy MAX with tUSDC
    md, ud = dear    # dear: sell MAX for tUSDC
    max_out = _out(D, uc, mc)
    usd_out = _out(max_out, md, ud)
    return usd_out - D


def scan():
    A, B = _mx_usd("PoolA"), _mx_usd("PoolB")
    pa, pb = A[1] / A[0], B[1] / B[0]                 # tUSDC per MAX
    if pa <= pb:
        cheap, dear, cheapR, dearR = A, B, "RouterA", "RouterB"
    else:
        cheap, dear, cheapR, dearR = B, A, "RouterB", "RouterA"
    lo, hi = min(pa, pb), max(pa, pb)
    # size: sample up to ~5% of the cheap pool's tUSDC depth
    dmax = cheap[1] // 20
    bp, bD, step = -(1 << 255), 0, max(1, dmax // 200)
    for i in range(1, 201):
        p = _profit(i * step, cheap, dear)
        if p > bp:
            bp, bD = p, i * step
    return {"hit": bp >= MIN_PROFIT, "gap": (hi / lo - 1) * 100, "borrow": bD / WAD,
            "profit": bp / WAD, "cheapR": cheapR, "dearR": dearR,
            "line": f"A {pa:.1f} / B {pb:.1f} | gap {(hi/lo-1)*100:.2f}% | size {bD/WAD:,.0f} | est {bp/WAD:+,.2f} tUSDC"}


def fire(s):
    me = ME
    usdc, mx = erc20("tUSDC"), erc20("MAX")
    cheapR, dearR = at(ADDR[s["cheapR"]], "Router"), at(ADDR[s["dearR"]], "Router")
    ensure_allowance("tUSDC", ADDR[s["cheapR"]], key=KEY)
    ensure_allowance("MAX", ADDR[s["dearR"]], key=KEY)
    D = int(round(s["borrow"] * WAD))
    u_before = usdc.functions.balanceOf(me).call()
    m_before = mx.functions.balanceOf(me).call()
    # leg 1: buy MAX on the cheap DEX (send() now raises if it reverts)
    send(cheapR.functions.swapExactTokensForTokens(D, 0, ADDR["tUSDC"], ADDR["MAX"], me), key=KEY)
    # robustly read what we actually received — public RPC can lag one node
    # behind right after the buy, returning a stale (0) balance. Poll until it
    # reflects the buy, so we never sell 0 MAX (which reverts and strands D).
    got_max = 0
    for _ in range(12):
        got_max = mx.functions.balanceOf(me).call() - m_before
        if got_max > 0:
            break
        time.sleep(0.5)
    if got_max <= 0:
        raise RuntimeError("buy landed but MAX balance still stale after poll — aborting sell")
    u_after_buy = usdc.functions.balanceOf(me).call()   # settled: ~ u_before - D
    # leg 2: sell that MAX on the dear DEX
    rcpt = send(dearR.functions.swapExactTokensForTokens(got_max, 0, ADDR["MAX"], ADDR["tUSDC"], me), key=KEY)
    # the sell always returns some tUSDC, so poll until the balance reflects it
    # (same public-RPC lag: a stale read here would under-report the profit).
    u_final = u_after_buy
    for _ in range(12):
        u_final = usdc.functions.balanceOf(me).call()
        if u_final > u_after_buy:
            break
        time.sleep(0.5)
    profit = (u_final - u_before) / WAD
    return {"tx": rcpt.transactionHash.hex(), "profit": profit}


if __name__ == "__main__":
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
