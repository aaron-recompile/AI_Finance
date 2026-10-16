"""arb_bot.py — SwapArbBot (flash-financed, zero capital).

Watch the two flash-demo DEXes (CHEAP @1950 / DEAR @2050). If a profitable
gap exists, size the optimal flash-borrow and fire the deployed Arbitrageur
(borrow -> buy cheap -> sell dear -> repay, one tx). Profit goes to the bot owner.

Uniform bot interface (used by orchestrator.py):
    NAME            : str
    scan() -> dict  : read-only; {"hit": bool, "line": str, "profit": float, ...}
    fire(s) -> dict : execute; {"tx": str, "profit": float}
"""
import sys
from chain import contract, erc20, send

NAME = "swap-arb"
WAD = 10 ** 18
SWAP_BPS, FLASH_BPS = 30, 5      # 0.3% per swap, 0.05% flash fee
MIN_PROFIT = 1 * WAD             # fire only if est. profit > 1 tUSDC


def _out(amount_in, r_in, r_out):
    a = amount_in * (10000 - SWAP_BPS)
    return a * r_out // (r_in * 10000 + a)


def _reserves():
    c, d = contract("CHEAP", "SimpleAMM"), contract("DEAR", "SimpleAMM")
    return (c.functions.reserve0().call(), c.functions.reserve1().call(),
            d.functions.reserve0().call(), d.functions.reserve1().call())


def _profit(D, R):
    Rc0, Rc1, Rd0, Rd1 = R
    max_out = _out(D, Rc1, Rc0)         # buy MAX on cheap
    usd_out = _out(max_out, Rd0, Rd1)   # sell MAX on dear
    return usd_out - (D + D * FLASH_BPS // 10000)


def _best(R, d_max=100_000 * WAD, steps=200):
    bp, bD, step = -(1 << 255), 0, d_max // steps
    for i in range(1, steps + 1):
        p = _profit(i * step, R)
        if p > bp:
            bp, bD = p, i * step
    return bp, bD


def scan():
    R = _reserves()
    pc, pd = R[1] / R[0], R[3] / R[2]
    profit, D = _best(R)
    return {"hit": profit >= MIN_PROFIT, "gap": (pd / pc - 1) * 100,
            "borrow": D / WAD, "profit": profit / WAD,
            "line": f"gap {(pd/pc-1)*100:.2f}% | borrow {D/WAD:,.0f} | est {profit/WAD:+,.2f} tUSDC"}


def fire(s):
    arb, usdc = contract("Arbitrageur"), erc20("tUSDC")
    owner = arb.functions.owner().call()
    before = usdc.functions.balanceOf(owner).call()
    rcpt = send(arb.functions.run(int(round(s["borrow"] * WAD))))
    realized = (usdc.functions.balanceOf(owner).call() - before) / WAD
    return {"tx": rcpt.transactionHash.hex(), "profit": realized}


if __name__ == "__main__":
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
