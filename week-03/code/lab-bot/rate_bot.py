"""rate_bot.py — RateArbBot (interest-rate arbitrage / iEarn).

Watch the supply APR of two lending venues (LendA, LendB). When the spread is
wide, shift a chunk of supplied capital from the lower-APR venue to the higher.
This both earns the better rate AND closes the gap (supplying lowers the target's
utilization) — the on-chain version of iEarn's rebalancing.

Interest is a *flow*, not a one-shot pop, so 'profit' here is the annualized APR
uplift on the moved size (value/year), logged as a rebalance action.
"""
import sys
from chain import at, ADDR, erc20, send, ensure_allowance, acct_of, load_bot_key

NAME = "rate-arb"
KEY = load_bot_key(NAME)          # this bot's own wallet
ME = acct_of(KEY).address
WAD = 10 ** 18
SIZE = 20_000 * WAD          # chunk to move per rebalance
MIN_SPREAD = 0.3 / 100       # act only if APR spread > 0.3%


def _apr(pool):
    return at(ADDR[pool], "LendingPool").functions.supplyAPR().call() / WAD


def scan():
    a, b = _apr("LendA"), _apr("LendB")
    (lo_p, lo), (hi_p, hi) = (("LendA", a), ("LendB", b)) if a <= b else (("LendB", b), ("LendA", a))
    spread = hi - lo
    low_cash = at(ADDR[lo_p], "LendingPool").functions.cash().call()
    can = low_cash >= SIZE
    return {"hit": spread > MIN_SPREAD and can, "spread": spread * 100,
            "from": lo_p, "to": hi_p, "hi_apr": hi * 100, "lo_apr": lo * 100,
            "value_per_yr": spread * SIZE / WAD,
            "line": f"{lo_p} {lo*100:.2f}% -> {hi_p} {hi*100:.2f}% | spread {spread*100:.2f}% | move {SIZE/WAD:,.0f} (+{spread*SIZE/WAD:,.0f}/yr)"}


def fire(s):
    lo = at(ADDR[s["from"]], "LendingPool")
    hi = at(ADDR[s["to"]], "LendingPool")
    ensure_allowance("tUSDC", ADDR[s["to"]], key=KEY)
    send(lo.functions.withdraw(SIZE), key=KEY)          # pull out of the low-APR venue
    rcpt = send(hi.functions.supply(SIZE), key=KEY)     # push into the high-APR venue
    # Interest is a FLOW, not a one-shot pop. For the classroom scoreboard we
    # "bank" the annualized yield uplift this rebalance locked in, so rate-arb
    # actually shows a score (it is value/YEAR, not instant tUSDC — say so in class).
    uplift = round(s["value_per_yr"], 1)
    return {"tx": rcpt.transactionHash.hex(), "profit": uplift,
            "value_per_yr": uplift,
            "note": f"moved {SIZE/WAD:,.0f} {s['from']}->{s['to']} (+{s['spread']:.2f}%/yr uplift, banked as score)"}


if __name__ == "__main__":
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
