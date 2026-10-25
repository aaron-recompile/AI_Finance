"""RiskAdjustedAllocator - Jingyou Ma's Track B mid-term strategy.

Deploys idle wallet tUSDC to the lending venue with the best yield after a
utilization-risk penalty. The bot keeps a cash reserve, limits its order relative
to pool liquidity, re-checks the signal before sending, and verifies receipt of
lending shares after confirmation.

Copy this file to week-03/code/lab-bot/ before running:
    python run.py my_strategy_bot
    python run.py my_strategy_bot --live
"""
import os
import time

from chain import ADDR, acct_of, at, ensure_allowance, erc20, send


NAME = "risk-adjusted-yield"
KEY = os.environ["AGENT_KEY"]
ME = acct_of(KEY).address

WAD = 10**18
MIN_ORDER = 10 * WAD
MAX_ORDER = 5_000 * WAD
RESERVE_BPS = 1_000          # keep 10% of wallet tUSDC liquid
MAX_POOL_CASH_BPS = 500      # one order <= 5% of venue cash
UTIL_PENALTY = 0.005         # subtract up to 0.5 percentage points at 100% utilization
MIN_SCORE = 0.001            # require at least 0.10% risk-adjusted annual yield
COOLDOWN_SECONDS = 300

_last_fire = 0.0


def _venue(name):
    pool = at(ADDR[name], "LendingPool")
    apr = pool.functions.supplyAPR().call() / WAD
    util = pool.functions.utilization().call() / WAD
    cash = pool.functions.cash().call()
    shares = pool.functions.shares(ME).call()
    score = apr - UTIL_PENALTY * util
    return {"name": name, "apr": apr, "util": util, "cash": cash,
            "shares": shares, "score": score}


def scan():
    """Rank lending venues and size a conservative deployment of idle tUSDC."""
    wallet = erc20("tUSDC").functions.balanceOf(ME).call()
    venues = [_venue("LendA"), _venue("LendB")]
    best = max(venues, key=lambda item: item["score"])

    spendable = wallet * (10_000 - RESERVE_BPS) // 10_000
    liquidity_cap = best["cash"] * MAX_POOL_CASH_BPS // 10_000
    amount = min(spendable, liquidity_cap, MAX_ORDER)
    cooldown_left = max(0, int(COOLDOWN_SECONDS - (time.time() - _last_fire)))
    hit = amount >= MIN_ORDER and best["score"] >= MIN_SCORE and cooldown_left == 0
    annual_yield = amount * best["apr"] / WAD

    return {
        "hit": hit,
        "pool": best["name"],
        "amount_wei": amount,
        "amount": amount / WAD,
        "apr": best["apr"] * 100,
        "util": best["util"] * 100,
        "score": best["score"] * 100,
        "annual_yield": annual_yield,
        "wallet": wallet / WAD,
        "cooldown": cooldown_left,
        "line": (
            f"{best['name']} APR {best['apr']*100:.2f}% | util {best['util']*100:.1f}% "
            f"| risk-adjusted {best['score']*100:.2f}% | deploy {amount/WAD:,.2f} tUSDC "
            f"| est +{annual_yield:,.2f}/yr"
            + (f" | cooldown {cooldown_left}s" if cooldown_left else "")
        ),
    }


def fire(signal):
    """Supply the quoted amount and verify that lending shares increased."""
    global _last_fire
    if not signal.get("hit"):
        raise RuntimeError("refusing to fire a stale or non-profitable quote")

    fresh = scan()
    if not fresh["hit"] or fresh["pool"] != signal["pool"]:
        raise RuntimeError("opportunity changed before execution; scan again")
    amount = min(int(signal["amount_wei"]), int(fresh["amount_wei"]))
    if amount < MIN_ORDER:
        raise RuntimeError("safe order size fell below the minimum")

    pool = at(ADDR[fresh["pool"]], "LendingPool")
    before = pool.functions.shares(ME).call()
    ensure_allowance("tUSDC", ADDR[fresh["pool"]], min_amount=amount, key=KEY)
    receipt = send(pool.functions.supply(amount), gas=300_000, key=KEY)
    after = pool.functions.shares(ME).call()
    received = after - before
    if received <= 0:
        raise RuntimeError("supply transaction landed but no lending shares were received")

    _last_fire = time.time()
    annual_yield = amount / WAD * fresh["apr"] / 100
    return {
        "tx": receipt.transactionHash.hex(),
        # A deposit creates a yield-bearing position but no immediately realized P&L.
        "profit": 0.0,
        "value_per_year": annual_yield,
        "supplied_tUSDC": amount / WAD,
        "shares_received": received / WAD,
        "pool": fresh["pool"],
        "note": "profit is expected annual interest, not instant realized P&L",
    }
