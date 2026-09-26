# AI Finance — Build Your Own On-Chain Autonomous Agent

Course materials for **MB / CSE 599 · AI Finance**. We don't just *study* blockchains — we *build* on them, and end the term with an AI **agent** that can hold assets, pay, and trade on-chain, safely, behind guardrails. **Everything uses testnets only — you never touch real money.**

> **New here? Start with [`SETUP.md`](SETUP.md).** It takes ~20 minutes and works on macOS / Windows / Linux.

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

---

## Week 3 — Composability → Bots on Chain

Snap the legos together into arbitrage and flash loans — first **by hand**, then let **bots** do it in one heartbeat.

| What | Where |
|------|-------|
| 🖥️ **Slides — Part 1: Composability** | [`week-03/slides/AI_Finance_Week3_Composability.html`](week-03/slides/AI_Finance_Week3_Composability.html) — legos → flash loans, done by hand |
| 🖥️ **Slides — Part 2: Bots on Chain (lab)** | [`week-03/slides/AI_Finance_Week3_Bots.html`](week-03/slides/AI_Finance_Week3_Bots.html) — the machines do it automatically |
| 🎮 **Interactive dApps** | [`week-03/app/`](week-03/app/) — `arb.html` (two-DEX arbitrage) · `flashloan.html` (zero-capital flash arb, one tx) |
| 📊 **Visualizations** | [`week-03/viz/`](week-03/viz/) — flash loan · interest-rate arb · leveraged carry |
| 🤖 **Bot lab (run it)** | [`week-03/code/lab-bot/`](week-03/code/lab-bot/) — 5 deterministic bots + a live dashboard. `pip install web3` then `./student_start.sh` (read-only, no wallet) and watch them detect on-chain opportunities the instant the market moves. |
| 💻 **Contracts (Foundry)** | [`week-03/code/flashloan-foundry/`](week-03/code/flashloan-foundry/) — FlashLender + Arbitrageur + SimpleAMM |

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
