# Prediction market — a minimal teaching skeleton

The third app in **one engine, three apps**: spot → perpetual → **prediction market**.

A prediction market trades **YES/NO conditional tokens** on a future event:
- a **YES** share pays **$1** if the event happens, **$0** if it doesn't
- a **NO** share pays **$1** if it doesn't, **$0** if it does

Three ideas fall out of that:

1. **YES price + NO price = $1**, always — holding one of each is a guaranteed $1.
2. **The YES price (0–1) is the probability** the market assigns to the event.
3. **Settlement is a one-time oracle call**: declare YES or NO, pay $1 to the winning side.

So a prediction market is like a **perpetual that settles exactly once, to 0 or 1** — same
matching idea, different payoff and a single final settlement instead of continuous funding.

## Run

```
python3 demo.py
```

It opens a market, takes a few YES/NO bets, lets the crowd move the price with "news",
then resolves and pays out — so you can watch the price act as a probability.

## Scope

This is a **deliberately tiny skeleton for teaching the concepts** — no order book, no real
collateral, no chain, and the price impact is a toy constant. A real prediction market
(e.g. Polymarket) adds an on-chain order book or AMM, USDC collateral held in a contract,
ERC-1155 outcome tokens, and an optimistic oracle (UMA) for resolution. Those are left out
on purpose; the point here is the payoff and why price = probability.
