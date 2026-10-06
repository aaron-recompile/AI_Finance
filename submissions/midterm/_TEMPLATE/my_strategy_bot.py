"""my_strategy_bot.py — YOUR mid-term strategy (Track B). Make it yours.

HOW TO USE
  1. Copy this file into  week-03/code/lab-bot/  (at the repo root) so it can `import chain`.
  2. Get a wallet funded by the instructor (see ../README.md), then:
         export AGENT_KEY=0xYOUR_PRIVATE_KEY        # never commit this
  3. Write your logic in scan() and fire() below.
  4. Test from inside week-03/code/lab-bot/:
         python run.py my_strategy_bot              # DRY-RUN (scan only, safe)
         python run.py my_strategy_bot --live       # LIVE (really trades)
  5. When it works, copy this file + NOTES.md into
         submissions/midterm/<your-github-username>/   and open a Pull Request.

Your bot must expose NAME, scan(), fire(s). Model it on the five example bots
(dex_arb_bot.py, rate_bot.py, farm_bot.py, liquidator_bot.py, arb_bot.py) — but the
IDEA must be yours, not a copy.

What you can read in scan() (see chain.py / the example bots):
  - DEX-A vs DEX-B prices (PoolA / PoolB)       -> spatial arbitrage
  - LendA vs LendB supply APR                   -> rate / carry
  - your own wallet balances                    -> sizing
  - the farm's pending rewards                  -> harvest timing
"""
import os
from chain import ADDR, at, contract, erc20, send, ensure_allowance, acct_of

NAME = "my-strategy"                         # shows up on the dashboard / leaderboard
KEY = os.environ["AGENT_KEY"]                # YOUR wallet — keep it out of git
ME = acct_of(KEY).address


def scan():
    """Read the chain and decide if there's an opportunity right now.
    Return a dict with at least:
        {"hit": True or False, "line": "<one human-readable line for the dashboard>"}
    plus any extra fields fire() needs (e.g. a size, which venue, ...).
    """
    # TODO: write your detection logic. Example starting points:
    #   price = usd_reserve / max_reserve of a pool
    #   gap   = max(priceA, priceB) / min(priceA, priceB) - 1
    return {"hit": False, "line": "my-strategy: write your scan() logic"}


def fire(s):
    """Called only when scan() returned hit=True AND you run with --live.
    Do your trade(s), signed by YOUR wallet, e.g.:
        router = at(ADDR["RouterA"], "Router")
        ensure_allowance("tUSDC", ADDR["RouterA"], key=KEY)
        rcpt = send(router.functions.swapExactTokensForTokens(amount, 0,
                    ADDR["tUSDC"], ADDR["MAX"], ME), key=KEY)
    Return a short result dict, e.g. {"tx": rcpt.transactionHash.hex(), "profit": got}.
    """
    # TODO: write your trade logic.
    raise NotImplementedError("write your fire() logic")
