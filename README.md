# AI Finance

**MB / CSE 599 · Graduate course · California Science and Technology University, Silicon Valley**
Fall 2026

A hands-on graduate course in on-chain finance and autonomous agents. Students build the on-chain stack from first principles — wallets and transactions, AMMs and lending, arbitrage and flash loans, a centralized exchange, perpetuals and prediction markets — and finish the term with an autonomous agent that holds assets, pays, and trades on-chain, behind explicit guardrails. All work is on public testnets.

This repository holds the full course: weekly materials and runnable code, interactive labs, concept videos, and readings.

> **New here? Start with [`SETUP.md`](SETUP.md).** ~20 minutes, on macOS / Windows / Linux.

> 🎬 **Concept videos — full-course companion:** short animated explainers spanning the course — from what a smart contract is (a vending machine), through DeFi, arbitrage and flash loans, autonomous agents, quant, and derivatives. One concept per video. Watch at **[aaron-recompile.github.io/AI_Finance/concept-videos](https://aaron-recompile.github.io/AI_Finance/concept-videos/)** (or see [`concept-videos/`](concept-videos/)).

> 🧪 **Labs:** the on-chain pieces are built from first principles — a clickable **AMM, lending, farming, arbitrage and flash-loan** set, an on-chain **bot arena**, and **three venues on one matching engine** (spot · perpetuals · prediction). See **[`labs/`](labs/)**.

> 📚 **Readings:** reading lists and pre-readings for each week — history, technical depth, and critical context, linking to free sources. See **[`readings/`](readings/)**.

---

## Week 1 — On-Chain Foundations

| What | Where |
|------|-------|
| 🛠️ **In class: setup + hands-on (start here)** | [`SETUP.md`](SETUP.md) — install the env, then the live loop: wallet → read chain → get test ETH → send to a classmate |
| 🖥️ **Slides (Session 1)** | [`week-01/slides/AI_Finance_Week1_Introduction.html`](week-01/slides/AI_Finance_Week1_Introduction.html) — open in a browser |
| 🖥️ **Slides (Session 2)** | [`week-01/slides/AI_Finance_Week1_IssueAsset.html`](week-01/slides/AI_Finance_Week1_IssueAsset.html) — make your own coin |
| 📖 **Lecture notes** | [`week-01/lecture-notes.md`](week-01/lecture-notes.md) |
| 📝 **Homework (after class)** | [`week-01/lab-exercise.md`](week-01/lab-exercise.md) |
| 📚 **Reference pack (terms + cheatsheet)** | [`week-01/foundations-reference-pack.md`](week-01/foundations-reference-pack.md) |
| 🎮 **Interactive demos** | [`week-01/demos/`](week-01/demos/) — open the `.html` files in a browser |
| 💻 **Code** | [`week-01/code/`](week-01/code/) |
| 🎬 **Concept video** | *A Contract = a Vending Machine* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

### The code (Week 1)

Run each after `conda activate ai_finance` (see `SETUP.md`):

| Script | What it does |
|--------|--------------|
| `read_chain.py` | Read a **live** blockchain: block height, gas, native ETH + USDC balance (read-only, free). Reads **Ethereum mainnet** by default. |
| `check_balance.py` | "Did my test ETH arrive?" — check any address's ETH + USDC on **any** chain (defaults to Base Sepolia). Never crashes on the wrong chain. |
| `gen_wallet.py` | Generate a wallet = a keypair (address + private key). **Testnet only.** |
| `send_asset.py` | Send native ETH: assemble → sign → broadcast → wait for inclusion. |
| `interact_contract.py` | Deploy a demo token, then `balanceOf` (read) and `transfer` (write). |
| `mini_amm.py` | A 20-line `x·y=k` AMM — see slippage grow with trade size. |
| `vending_machine.py` | A contract = a vending machine made of math (text demo of "no operator to trust"). |

### The 5-rung ladder (how we learn every topic)

**R1** see it → **R2** use it in a wallet/site → **R3** drive it with code → **R4** build it → **R5** hand it to your agent. *Where you stop is your track.*

---

## Week 2 — DeFi Legos: AMM + Lending

The building blocks. Swap on an AMM, then supply/borrow on a lending market — and see a liquidation.

| What | Where |
|------|-------|
| 🖥️ **Slides — AMM** | [`week-02/slides/AI_Finance_Week2_AMM.html`](week-02/slides/AI_Finance_Week2_AMM.html) — `x·y=k`, price, slippage |
| 🖥️ **Slides — Lending** | [`week-02/slides/AI_Finance_Week2_Lending.html`](week-02/slides/AI_Finance_Week2_Lending.html) — supply/borrow, health factor, liquidation |
| 🎮 **Interactive dApps** | [`week-02/app/`](week-02/app/) — `v2.html` (AMM swap) · `lend.html` (lending) · `farm.html` (yield farming: mine & dump) |
| 📊 **Visualizations** | [`week-02/viz/`](week-02/viz/) — AMM swap · lending & liquidation |
| 💻 **Code** | [`week-02/code/`](week-02/code/) — `amm.py` · `lend.py` · `lend_demo.py`; Foundry: `amm-foundry` (SimpleAMM) · `lend-foundry` (SimpleLend) |
| 🎬 **Concept videos** | *What is an AMM* · *Lending & Liquidation* · *Yield Farming* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

---

## Week 3 — Composability → Bots on Chain

Snap the legos together into arbitrage and flash loans — first **by hand**, then automatically with **bots**.

| What | Where |
|------|-------|
| 🖥️ **Slides — Part 1: Composability** | [`week-03/slides/AI_Finance_Week3_Composability.html`](week-03/slides/AI_Finance_Week3_Composability.html) — legos → flash loans, done by hand |
| 🖥️ **Slides — Part 2: Bots on Chain (lab)** | [`week-03/slides/AI_Finance_Week3_Bots.html`](week-03/slides/AI_Finance_Week3_Bots.html) — the machines do it automatically |
| 🎮 **Interactive dApps** | [`week-03/app/`](week-03/app/) — `arb.html` (two-DEX arbitrage) · `flashloan.html` (zero-capital flash arb, one tx) |
| 📊 **Visualizations** | [`week-03/viz/`](week-03/viz/) — flash loan · interest-rate arb · leveraged carry |
| 🤖 **Bot lab (run it)** | [`week-03/code/lab-bot/`](week-03/code/lab-bot/) — 5 deterministic bots + a live dashboard. `pip install web3` then `./student_start.sh` (read-only, no wallet) and watch them detect on-chain opportunities the instant the market moves. |
| 💻 **Contracts (Foundry)** | [`week-03/code/flashloan-foundry/`](week-03/code/flashloan-foundry/) — FlashLender + Arbitrageur + SimpleAMM |
| 🎬 **Concept videos** | *What is Arbitrage* · *What is a Flash Loan* · *Bots vs Manual* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

---

## Week 4 — From Program to Agent (OpenClaw)

Your bots were **hands** you drove. This week a **brain** runs them on its own, behind guardrails — an autonomous agent you interact with over Telegram.

| What | Where |
|------|-------|
| 🖥️ **Slides** | [`week-04/slides/AI_Finance_Week4_OpenClaw.html`](week-04/slides/AI_Finance_Week4_OpenClaw.html) — program → agent; *brain judges, hands execute* |
| 💬 **Demo prompts** | [`week-04/prompts/jarvis-demo-prompts.md`](week-04/prompts/jarvis-demo-prompts.md) — what to say to the agent, organized by lego |
| 🤖 **Example skills** | [`week-04/skills/`](week-04/skills/) — real `SKILL.md` recipes (swap · lend · flash-arb) + the `USER.md` standing-rules fence (sanitized) |
| 📝 **Overview** | [`week-04/README.md`](week-04/README.md) |
| 🎬 **Concept video** | *Brain and Hands (Program vs Agent)* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

Every money action **plans → waits for your `confirm` → executes → verifies on-chain → reports**. The LLM never sizes a trade, never signs, never sees the key.

---

## Week 5 — CEX: the Execution Layer (OKX + Alpaca) + Cash-and-Carry

After building our own on-chain primitives, we drop to the **centralized execution layer**: how you actually talk to an exchange/broker over an API, and how a market-neutral **cash-and-carry** pays once fees are counted. **Paper / demo money only; keys come from your env or the macOS keychain, never hard-coded.**

| What | Where |
|------|-------|
| 🖥️ **Slides** | [`week-05/slides/AI_Finance_Week5_CEX.html`](week-05/slides/AI_Finance_Week5_CEX.html) — CEX vs DEX, order types, cash-and-carry |
| 📝 **Overview** | [`week-05/README.md`](week-05/README.md) |
| 💻 **Code** | [`week-05/code/`](week-05/code/) — `okx/` (connect · history · orders · websocket) · `strategies/` (`trend_follow` · `mean_reversion` · `cash_and_carry` · `carry_run`) · `alpaca/` (stocks, paper) · `jarvis-okx-carry/` (the agent running carry behind a gate) |
| 🎬 **Concept videos** | *Common Quant Strategies* · *Quant Metrics 101* · *What is Cash-and-Carry* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

---

## Week 6 — Derivatives: Perps on Hyperliquid (+ Polymarket)

The agent stops trading the present and starts trading the **future**: funding on perpetuals, and the probability of an event. The code is the **Hyperliquid** half — read the on-chain order book and funding, place/cancel orders, replay a strategy honestly, run a two-leg **funding-carry** bot. **Hyperliquid testnet only; keys from local, gitignored files.** The prediction-market half ships as a minimal teaching skeleton.

| What | Where |
|------|-------|
| 🖥️ **Slides** | [`week-06/slides/AI_Finance_Week6_Derivatives.html`](week-06/slides/AI_Finance_Week6_Derivatives.html) — perps · funding · prediction markets |
| 📝 **Overview** | [`week-06/README.md`](week-06/README.md) |
| 💻 **Code — Hyperliquid** | [`week-06/code/hyperliquid/`](week-06/code/hyperliquid/) — `book` · `funding` · `hl_read` · `hl_trade` · `hl_replay` · `hl_carry_bot` · `hl_agent` |
| 💻 **Code — Polymarket** | [`week-06/code/polymarket/`](week-06/code/polymarket/) — minimal prediction-market skeleton (`prediction_market.py` · `demo.py`) |
| 🎬 **Concept videos** | *What is a Perpetual* · *What is Hyperliquid* · *What is Polymarket* · *Futures & Options Basics* · *Obligation or Right* · *Three Anchors* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

---

## Week 7 — x402 & Farcaster: Pay and Speak

For six weeks the agent learned to **earn**. Week 7 adds the last two verbs — to **pay**, and to **speak**. An agent that earns, pays, and speaks is an **economic actor**, not just a tool. **Testnet / tiny amounts only; keys from env or a gitignored `.env`, never committed.**

| What | Where |
|------|-------|
| 🖥️ **Slides** | [`week-07/slides/AI_Finance_Week7_x402_Farcaster.html`](week-07/slides/AI_Finance_Week7_x402_Farcaster.html) — Pay and Speak |
| 📝 **Overview** | [`week-07/README.md`](week-07/README.md) |
| 💻 **Pay — x402** | [`week-07/code/x402/`](week-07/code/x402/) — pay-per-call USDC on Base; `x402_agent.py` runs with no setup, behind a spend fence (per-call/daily cap + seller allowlist) |
| 💬 **Speak — Farcaster** | [`week-07/code/farcaster/`](week-07/code/farcaster/) — post in public with `cast.py`; preview by default, `--yes` to send, every post human-gated |
| 🎬 **Concept videos** | *What is x402* · *The Agent Economy* · *What is Farcaster* → [watch](https://aaron-recompile.github.io/AI_Finance/concept-videos/) |

---

## Week Final — Capstone & Wrap-Up

Look back at the whole arc, where everything lives, where to go next on your own — and a walkthrough where one agent runs the entire course.

| What | Where |
|------|-------|
| 🖥️ **Wrap-up slides** | [`week-final/slides/AI_Finance_Final_WrapUp.html`](week-final/slides/AI_Finance_Final_WrapUp.html) — the arc, where it lives, required vs extra, the design on purpose |
| 🖥️ **Depth & self-study slides** | [`week-final/slides/AI_Finance_Final_Depth-and-SelfStudy.html`](week-final/slides/AI_Finance_Final_Depth-and-SelfStudy.html) — honest limits + a path to keep going |
| 🤖 **Agent walkthrough (prompts)** | [`week-final/agent-prompts/`](week-final/agent-prompts/) — one-line prompts that make an agent run the whole course week by week, plus the guardrails that make it stop |

---

## Repository layout

Each week is one folder with the same shape — look in the same place every week:

```
week-NN/
  slides/    decks, named AI_Finance_Week<N>_<Topic>.html
  demos/     open-in-browser interactive .html
  code/      runnable scripts and Foundry projects
  *.md       lecture-notes · lab-exercise · hands-on · reference pack
```

---

## Golden rule

**Testnets only. Never put real money behind a demo key.** A private key is everything — never paste it into a website, a chat, or a shared file.
