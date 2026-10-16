# Mid-term Project — Make Something That Trades On-Chain

**Due: Oct 18.** Pick ONE track (A or B). You may switch tracks for the Final.

You've watched the class arena — real contracts on Base Sepolia, bots with their own
wallets, a live leaderboard. Now you build your own thing that lives in that world.

---

## Track A — The Agent  (AI / OpenClaw)

Stand up your OWN OpenClaw, give it a wallet, and deploy one of the strategies we built
(e.g. the DEX arbitrage) so your agent does a real on-chain action **on its own**.

**Minimum to pass**
1. OpenClaw running (your machine or the class host) — screenshot.
2. Your agent deployed with its own wallet, pointed at the class arena contracts.
3. It autonomously performs at least one real on-chain action (swap / arbitrage /
   harvest) — give the transaction hash.

**Submit (PDF):** OpenClaw-running screenshot · your agent's wallet address · tx hash(es)
on Basescan · 3–5 sentences on what your agent does and why that action is correct.

→ Golden path: [`track-a-openclaw/README.md`](track-a-openclaw/README.md) (builds on [`../../week-04/`](../../week-04/)).

---

## Track B — The Strategist  (your own bot)

Write your OWN strategy bot — NOT one of the five we provided — and run it in the arena
with your own wallet so it competes on the leaderboard.

**Minimum to pass**
1. The arena runs for you (you can read the market and your wallet).
2. You write an original strategy (`scan()` + `fire()`) — it must be *yours*, not a copy
   of the provided bots.
3. It fires at least one real on-chain action from your wallet and shows on the
   leaderboard — give tx hash + a leaderboard screenshot.

**Submit:** your bot file + `NOTES.md` in `submissions/midterm/<your-github-name>/` (via a
Pull Request), plus a PDF: your wallet address · tx hash(es) · a leaderboard screenshot ·
3–5 sentences on what your strategy does and why it should make money.

### Track B — how to do it

```
submissions/midterm/
  <your-github-username>/     <- you create this, put your work here
    my_strategy_bot.py
    NOTES.md
  _TEMPLATE/                  <- copy this to start; do NOT edit _TEMPLATE itself
```

1. **Get a wallet.** Create one and send the **address** to the instructor to fund it
   (gas + tUSDC). Put the key in an env var — never commit it:
   ```
   export AGENT_KEY=0xYOUR_PRIVATE_KEY
   ```
2. **Develop inside the lab.** Copy `_TEMPLATE/my_strategy_bot.py` into
   [`../../week-03/code/lab-bot/`](../../week-03/code/lab-bot/) so it can `import chain`
   like the example bots. Write your own `scan()` + `fire()` there and test it:
   ```
   python run.py my_strategy_bot            # DRY-RUN (scan only, safe)
   python run.py my_strategy_bot --live     # LIVE (really trades with AGENT_KEY)
   ```
   Model it on the five example bots — but the idea must be **yours**, not a copy.
3. **Submit.** Copy your finished bot + a filled-in `NOTES.md` into
   `submissions/midterm/<your-github-username>/`, commit, and open a Pull Request.

**Rules:** never commit a private key · only add files under your own folder · don't edit
the reference code, `_TEMPLATE/`, or anyone else's folder · keep the diff to your folder.
We grade in the PR and don't merge student answers into the reference code — your folder is
yours.

---

## How this grows into the Final  (same track, scaled up)

- **Track A → Final:** your agent goes **multi-venue** — add a centralized-exchange /
  Hyperliquid action, so one agent trades both DeFi and a CEX / perp market.
- **Track B → Final:** a **bigger strategy** — cross-venue arbitrage (CEX↔DEX or
  cross-exchange), or a funding / basis trade on Hyperliquid.

Mid-term = get ONE thing working. Final = make it bigger and smarter.
**Keep your mid-term code — you will build directly on it.**

---

## Honesty note

You may use AI to help write code, but you must be able to explain **why it works**.
"The AI wrote it" is not an answer. For Track B especially, be ready to explain why your
strategy should be profitable — and what would make it lose.

## Rubric (100)

| | |
|---|---|
| Runs + a real on-chain action | 45 |
| Originality (genuinely your own) | 25 |
| Correctness + you can explain it | 20 |
| Clear writeup + on-chain evidence | 10 |
| Bonus: leaderboard rank / Track A LLM-in-the-loop | up to +10 |

## Submitting (by Oct 18)

- Both tracks: a PDF in Google Classroom.
- Track B also opens a Pull Request adding **only** `submissions/midterm/<your-name>/`.
- Questions → class comments or office hours.
