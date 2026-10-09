# Week 6 — Derivatives: perps on Hyperliquid, and funding carry

Week 5 was the CEX execution layer. Week 6 moves to **derivatives**: the agent stops trading
the present and starts trading the **future** — funding on perpetuals, and (in the lecture) the
probability of an event.

The code here is the **Hyperliquid** half: read the on-chain order book and funding, place and
cancel orders, replay a strategy honestly, and run a two-leg **funding-carry** bot. Everything is
**Hyperliquid testnet only**. Keys are read from local, gitignored files — never committed.

> The prediction-market half of the lecture is taught through a hosted demo, not shipped here.

## Slides
- `slides/AI_Finance_Week6_Derivatives.html`

## Code (`code/hyperliquid/`)

Four beats, same shape as Week 5 (read → order → strategy → agent):

| Beat | Files | What |
|---|---|---|
| Read (no wallet) | `hl_read.py` · `book.py` · `funding.py` · `hl_signals.py` · `hl_history.py` | OI / funding / order book / funding screener + slippage / candles + funding history |
| Order structure | `hl_dryrun.py` | sign a real order and print it, never submit |
| Place / cancel | `hl_trade.py` | testnet: check account, rest an order far from the book, cancel it |
| Agent wallet | `hl_agent.py` | a trade-only API wallet places/cancels for the master account |
| Feel funding | `hl_funding.py` | open a small short, watch funding land each hour, read the ledger |
| Replay | `hl_replay.py` | naive backtest vs honest replay (how overtrading feeds profit to slippage) |
| Carry bot | `hl_carry_bot.py` | the two-leg funding-carry bot (long spot + short perp), with rules, alerts, and a kill-switch |

## Setup

Reads need nothing. For the order/agent/carry scripts, copy the example env files and fill in your
**testnet** keys (both are gitignored):

```bash
cp .env.example .env               # PRIVATE_KEY  (used by hl_dryrun.py, hl_trade.py)
cp .agent.env.example .agent.env   # AGENT_PRIVATE_KEY + MASTER_ADDRESS  (used by hl_agent.py, hl_funding.py, hl_carry_bot.py)
```

- `AGENT_PRIVATE_KEY` is a **trade-only API wallet** approved on Hyperliquid — it can trade but cannot withdraw. `MASTER_ADDRESS` is the main account the orders are booked under.
- Get testnet USDC from the Hyperliquid testnet faucet before running the order scripts.
- Dependencies: `pip install hyperliquid-python-sdk eth-account requests`.

## The carry bot

`hl_carry_bot.py` is the funding-carry strategy wrapped as a runnable bot: long spot POBTC + short
BTC perp (delta-neutral), collecting funding while the basis holds. It runs one `tick` per hour,
books a two-leg ledger, and applies hard rules — close when the basis shrinks / funding flips /
loss hits the cap / 7 days pass, alert (with cooldown) when the basis widens or the spot bid dries
up, and halt on a `STOP` file. It prints `NO_REPLY` when nothing's up and a paragraph when it is,
which is the contract an OpenClaw cron job uses to decide whether to message you.

P&L = funding (the rent) + basis change − fees. Same lesson as Week 5's carry: the edge is thin and
fees/slippage decide it, so you measure it by the week.
