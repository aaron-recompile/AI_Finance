# Track A — The Agent (OpenClaw) · golden path

Goal: stand up your OWN OpenClaw, give it a wallet, and have it do a real on-chain action
in the class arena — **on its own**.

Start from the Week-4 material: [`week-04/`](../../../week-04/) (slides + prompts +
skills examples). This page is the 5-step checklist.

## 5 steps

1. **Install / open OpenClaw.** Follow the Week-4 README. If you can't install it on your
   own machine, ask the instructor about running on the class host.

2. **Give your agent a wallet.** Create a wallet for the agent and send its **address** to
   the instructor to fund (gas + tUSDC) — same as a lab wallet. Keep the private key in an
   env var, never in a file you commit.

3. **Give it the arena.** The contract addresses are in
   [`week-03/code/lab-bot/chain.py`](../../../week-03/code/lab-bot/chain.py) (and
   `deployed.json`). Point your agent's tools at the Base Sepolia RPC and those addresses,
   so it can read prices and send transactions.

4. **Give it ONE job we learned.** For example: *"Watch DEX-A vs DEX-B. When the price gap
   is big enough to beat fees and slippage, buy MAX on the cheaper DEX and sell it on the
   dearer one."* Let the agent decide and act — you are not clicking the trade, it is.

5. **Make it happen and capture proof.** Trigger an opportunity (ask the instructor to skew
   the market, or create one yourself), then capture: a screenshot of OpenClaw running and
   deciding, and the resulting transaction hash on Basescan.

## Submit (PDF)

OpenClaw-running screenshot · your agent's wallet address · the tx hash(es) on Basescan ·
3–5 sentences on what your agent does and why that action is correct.

## The leap (bonus)

Let the agent's **decision** come from the LLM reading the live market, not a hard-coded
`if gap > x`. That is what turns a *bot* into an *agent* — and it's the Final's direction.

## If OpenClaw won't install (safety net)

Talk to the instructor: run on the class host, pair up, or fall back to Track B. Nobody
should be blocked by an install.
