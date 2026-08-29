# AI Finance — Build Your Own On-Chain Autonomous Agent

Course materials for **MB / CSE 599 · AI Finance**. We don't just *study* blockchains — we *build* on them, and end the term with an AI **agent** that can hold assets, pay, and trade on-chain, safely, behind guardrails. **Everything uses testnets only — you never touch real money.**

> **New here? Start with [`SETUP.md`](SETUP.md).** It takes ~20 minutes and works on macOS / Windows / Linux.

---

## Week 1 — On-Chain Foundations

| What | Where |
|------|-------|
| 🛠️ **In class: setup + hands-on (start here)** | [`SETUP.md`](SETUP.md) — install the env, then the live loop: wallet → read chain → get test ETH → send to a classmate |
| 🖥️ **Slides (Session 1)** | [`week-01/slides/AI_Finance_Week1.html`](week-01/slides/AI_Finance_Week1.html) — open in a browser |
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
| `agent_tools.py` | Wrap the ops as **agent tools behind guardrails** (per-tx cap + whitelist). |
| `vending_machine.py` | A contract = a vending machine made of math (text demo of "no operator to trust"). |
| `faucet_distribute.py`, `reclaim.py` | *Instructor tools:* batch-fund student wallets / sweep testnet ETH back. |

### The 5-rung ladder (how we learn every topic)

**R1** see it → **R2** use it in a wallet/site → **R3** drive it with code → **R4** build it → **R5** hand it to your agent. *Where you stop is your track.*

---

## Golden rule

**Testnets only. Never put real money behind a demo key.** A private key is everything — never paste it into a website, a chat, or a shared file.
