# Week 5 — CEX: the execution layer (OKX + Alpaca), and cash-and-carry

After building our own on-chain primitives, Week 5 is about the **centralized execution
layer**: how you actually talk to an exchange / broker over an API, and how a simple
market-neutral arbitrage (cash-and-carry) really pays off once fees are counted.

Everything here runs on **paper / demo money only**. No live trading, no withdrawals.
Credentials are always read from your environment or the macOS keychain — never hard-coded.

## Slides
- `slides/AI_Finance_Week5_CEX.html`

## Code (`code/`)

Grouped by what it does:

| Folder | Files | What |
|---|---|---|
| `okx/` | `okx_client` · `okx_orders` · `okx_ws_listen` · `okx_history` | basic OKX operations: auth + REST orders + live WebSocket + history (demo market) |
| `strategies/` | `trend_follow` · `mean_reversion` · `cash_and_carry` · `carry_run` | three strategies — two **bet on direction** (trend-following, mean-reversion), one is **market-neutral** (cash-and-carry). `carry_run` trades one real carry round on OKX demo. |
| `alpaca/` | `alpaca_client` · `alpaca_orders` · `alpaca_read` · `alpaca_env.sh` | the same read / place / amend / cancel pattern on Alpaca paper (stocks + crypto) |
| `jarvis-okx-carry/` | `carry_agent` · `carry_gate` · `skill/` | the carry handed to an OpenClaw agent: plan → a 6-digit token → human says `CONFIRM` → execute, demo only, with guardrails |

The three simple strategies run on public data with **no key** — just `cd strategies` then:
```
python3 trend_follow.py        # hold above the 50-day MA (crash insurance)
python3 mean_reversion.py      # buy oversold, sell the bounce (RSI(2))
python3 cash_and_carry.py      # long spot + short perp = market-neutral, earn funding
```
Trend and mean-reversion bet on **price direction**; cash-and-carry does **not** — it nets the
funding rate while staying delta-neutral.

Set up credentials to place orders:
- OKX: export `OKX_API_KEY` / `OKX_SECRET` / `OKX_PASSPHRASE` (demo keys). Used by `okx/okx_orders.py` and `strategies/carry_run.py`.
- Alpaca: `source alpaca/alpaca_env.sh` (pulls a paper key from the macOS keychain).

## The real carry round (the teaching gold)

`strategies/carry_done_*.json` is one actual round on OKX demo: long 0.0119 BTC spot + short 1.19
BTC-USDT-SWAP contracts, closed ~2 hours later.

- **result = −2.595 USDT** (funding **−0.46**, fees **−2.11**)

It **lost money, because fees ate everything.** That is exactly the lesson: the carry spread
is thin, **fees are the main character**, you measure it by the week, and a backtest flatters
you until a live round pushes back with a real negative number.

## OKX demo vs Alpaca paper — the execution layer compared

Same four actions on both (read → place → amend → cancel), but the plumbing differs:

| | OKX Demo | Alpaca paper |
|---|---|---|
| Identity | exchange (matches orders itself) | **broker** (routes to a venue, one extra hop → `pending_new`) |
| Credentials | key + secret + passphrase | key + secret |
| Auth | secret never leaves, HMAC-sign every call (three gotchas) | two headers sent directly, no signature |
| Paper switch | header `x-simulated-trading: 1` | **a different domain** `paper-api`; key starts with `PK` |
| Domains | one `www.okx.com` | two: trading `paper-api`, data `data` |
| Leverage/short | spot mode `acctLv=1` can't trade perps, switch to mode 2 | margin account by default: 4× buying power, `shorting_enabled` |
| Hours | 24/7 | stocks have an open/close (`/v2/clock`); crypto 24/7 |
| Time-in-force | optional | **required**; crypto only accepts gtc/ioc |
| Min order | by coin quantity | crypto by **limit price × qty ≥ $10** (else 403) |
| States | live → filled/canceled | pending_new → new → filled/canceled/replaced |
| Amend | same `ordId` (loses queue priority) | **new order, new id**, old one `replaced`; a PATCH without `client_order_id` gets a random UUID → keep your own with `-r1` |
| Success/failure | HTTP 200 + `code`/`sCode` | HTTP status: 204 ok · 403 rule reject · 422 wrong state |
| Cancel a filled order | `sCode 51400` (filled/canceled/not-found all in one) | 422 `already in "filled" state` (explicit) |
| Symbol spelling | `BTC-USDT` | order `BTC/USD`, position `BTCUSD` |
| Free-data gotcha | reading tickers one by one → a fake spread | IEX feed is only 2–3% of volume; after-hours quotes are junk |

### Measured round-trip cost (market buy → ~1 min later market sell, BTC)

| | OKX Demo | Alpaca paper |
|---|---|---|
| Quantity | 0.0001 | 0.0002 (0.0001995 received) |
| Buy / sell avg | 83,609.9 / 83,595.6 | 83,647.04 / 83,599.32 |
| Taker fee | ~0.07% | **0.25%** |
| Round-trip total | ~**0.16%** of notional | ~**0.56%** of notional |
| Of which fees | ~90% | ~90% |

**Takeaway:** a round trip is mostly fees. The broker is ~3.5× more expensive for crypto, so
crypto arbitrage goes on OKX and Alpaca is used for stocks.
