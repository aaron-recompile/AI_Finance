---
name: okx-carry
description: Run the boss's OKX DEMO (paper) cash-and-carry arbitrage -- long BTC spot + short BTC-USDT-SWAP perp -- with a plan -> boss says CONFIRM -> execute flow. Use when the boss asks to open / check / close an OKX carry, or replies "close" after an OKX carry alert. NOT for the Hyperliquid carry (that is the `carry` skill).
---

# OKX carry (demo) -- plan, confirm, execute

Two-leg carry on **OKX Demo Trading only** (fake money): buy BTC spot + short the same amount of
BTC perp. Direction cancels; P&L = funding + basis change - fees.
Executor: `carry_agent.py` (ships beside this skill, in `code/jarvis-okx-carry/`). It reads the API
key itself -- **you never read, print, copy or ask for `~/.secrets/okx-demo.env` or any key.**

Run everything from the `jarvis-okx-carry` dir with `python3 carry_agent.py <cmd>`.

## The one rule: plan -> boss says CONFIRM -> execute

1. Boss asks to open (e.g. "open an OKX carry, 1000"):
   run `plan-open --usdt <amount>` (default 1000, max 2000). Send the boss the plan text **as is**.
   It ends with a 6-digit token. Keep the token to yourself -- do not ask the boss to type it.
2. **Wait.** Only when the boss's next message is an explicit CONFIRM / yes for THIS plan,
   run `open --confirm <token>`. Anything else (questions, "wait", silence, a different amount)
   -> do NOT execute; answer or make a new plan.
3. Report the executor's output as is. If it starts with X, nothing (or a rollback) happened --
   say so plainly, then run `check` and report.

Closing is the same: `plan-close` -> send plan -> boss says CONFIRM -> `close --confirm <token>`.
When the boss replies "close" to an alert, that means "make a close plan", not "close now".

A token works once, expires after 10 minutes, and dies if price moved > 0.3%. If expired,
just make a new plan and ask again. Never re-use, guess or invent a token.

## Read-only commands (no confirmation needed)

- `check` -- account mode, balances, whether a round is open
- `status` -- the open round's P&L and whether any exit rule fired

## Explaining (the boss's mental model -- use these words)

- The two legs summed are the real P&L; the spot leg and perp leg being one positive one negative is normal = the hedge working.
- P&L = funding (the rent) + basis change - fees. Fees are usually the biggest piece, so carry is measured by the week.
- OKX demo is a separate market: its prices and funding rate differ from live; the demo numbers are for practicing the flow, not for real.
- Exit rules: funding negative 3 periods in a row / held 7 days / unrealized loss over 20 USDT. When one fires it only alerts; whether to close is the boss's call.

## Never

- Never open or close without a fresh token from a plan the boss confirmed in this conversation.
- Never edit carry_agent.py / carry_gate.py, its limits, or the state files.
- Never touch real (non-demo) trading, withdrawals, transfers, or account settings
  (e.g. switching account mode -- tell the boss to do it in the OKX demo UI instead).
- Never create cron jobs or timers for this. The gate job already exists.
- Never promise checks the executor does not do. It only checks: an open round already exists,
  token/expiry/0.3% price drift, 0.1% slippage cap per leg, and rolls back if the perp leg under-fills.
