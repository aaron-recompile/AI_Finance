"""liquidator_bot.py — LiquidatorBot.

Watch borrowers' health factor on a LendingPool. When someone falls below
HF < 1 (e.g. the instructor cut the oracle price), repay their debt and seize
their collateral at a +10% bonus. Profit = seized collateral value - debt repaid.
"""
import sys
from chain import at, ADDR, erc20, send, ensure_allowance, acct_of, load_bot_key, BORROWER

NAME = "liquidator"
KEY = load_bot_key(NAME)          # this bot's own wallet
ME = acct_of(KEY).address
WAD = 10 ** 18
POOL = "LendB"           # the venue that has a borrower position
WATCH = [BORROWER]       # accounts to monitor (extend as needed)
MIN_DEBT = 100 * WAD     # ignore dust positions


def _pool():
    return at(ADDR[POOL], "LendingPool")


def scan():
    p = _pool()
    worst = None
    for u in WATCH:
        debt = p.functions.currentDebt(u).call()
        if debt == 0:
            continue
        hf = p.functions.healthFactor(u).call()
        if worst is None or hf < worst[1]:
            worst = (u, hf, debt)
    if worst is None:
        return {"hit": False, "line": "no borrowers"}
    u, hf, debt = worst
    return {"hit": hf < WAD and debt >= MIN_DEBT, "user": u, "hf": hf / WAD, "debt": debt / WAD,
            "line": f"borrower {u[:8]}… HF {hf/WAD:.3f} | debt {debt/WAD:,.0f} tUSDC"}


def fire(s):
    p = _pool()
    me = ME
    usdc, mx = erc20("tUSDC"), erc20("MAX")
    ensure_allowance("tUSDC", ADDR[POOL], key=KEY)
    u_before, m_before = usdc.functions.balanceOf(me).call(), mx.functions.balanceOf(me).call()
    rcpt = send(p.functions.liquidate(s["user"], int(round(s["debt"] * WAD))), key=KEY)
    if rcpt.status != 1:
        # reverted -> the price was healed or another keeper beat us to it
        return {"tx": rcpt.transactionHash.hex(), "profit": 0.0, "note": "reverted (healed or beaten to it)"}
    price = p.functions.price().call() / WAD
    paid = (u_before - usdc.functions.balanceOf(me).call()) / WAD
    seized = (mx.functions.balanceOf(me).call() - m_before) / WAD
    return {"tx": rcpt.transactionHash.hex(), "profit": seized * price - paid,
            "seized_MAX": seized, "paid_tUSDC": paid}


if __name__ == "__main__":
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
