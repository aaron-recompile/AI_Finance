# Week 1 Lab (Homework): Touch the Chain

**Weight:** counts toward weekly Labs. **Due:** before Week 2, Session 3. **Late turn-in accepted** (marked late) — don't skip it.
**Prerequisite:** finish [`SETUP.md`](../SETUP.md) (Python env + `web3` + cloned repo). Every terminal: activate your `ai_finance` env first — your prompt must show `(ai_finance)`.
**Note:** run scripts with plain `python` inside the `ai_finance` env. Write-state scripts run on **Base Sepolia testnet** using the test ETH you got in class (no local node needed). 🪟 Windows: set variables with `set VAR=value` on their own line (no space after `=`).

## Goal

*Touch* this objective world by hand: prove your environment, **read** the chain for free, and **send** an asset to a classmate — the R1→R3 arc of Week 1. No magic left standing.

## Steps (everyone)

1. **Environment proof.** Paste into `reflection.md`:
   ```bash
   python --version
   python -c "import web3, eth_account; print('web3', web3.__version__)"
   ```
   Plus the output of `check_balance.py` on **your** funded testnet address, showing your test ETH:
   ```bash
   # 🍎 macOS/Linux
   ADDR=0xYourAddress python check_balance.py
   # 🪟 Windows: set ADDR=0xYourAddress   then   python check_balance.py
   ```
2. **Read the chain.** Run `code/read_chain.py`, paste the output. One sentence: *what did you read, and why did it cost nothing and need no login?*
3. **Send a native asset to a classmate.** On Base Sepolia, send a small amount with your own key:
   ```bash
   RPC=https://base-sepolia-rpc.publicnode.com PRIVATE_KEY=0xYOURkey TO=0xCLASSMATE AMOUNT_ETH=0.0002 python send_asset.py
   ```
   Paste the before/after balances and the tx hash. One sentence: *from pressing enter to the asset arriving, what steps did the transaction go through?*
4. **(Optional — preview of Week 2) Interact with a contract (read + write).** `code/interact_contract.py` deploys a demo token, then does `balanceOf` (read) and `transfer` (write). It needs a local `anvil` node — that's **Foundry, which we install in Week 2** — so this step is optional now. If you already have `anvil`, run it and answer: *what's the essential difference between `balanceOf` (read) and `transfer` (write) — why is one free and the other a transaction?*

## Deliverables (push to your repo)

- `reflection.md` — all answers above, plus the `check_balance.py` proof (your test ETH) and the send tx hash.
- (Optional) your tweaked `read_chain.py` if you modified it.

## Grading (10 pts)

| Criterion | Pts |
|-----------|-----|
| Environment proof complete (versions + `check_balance.py` shows your test ETH) | 3 |
| Read the chain runs, question answered correctly | 2 |
| Send to a classmate runs (tx hash + before/after), question answered | 4 |
| Contract read vs write explained (optional preview, or a written answer) | 1 |

## Prompts you can use

- *"Explain what a JSON-RPC endpoint is, like I've never used one."*
- *"Walk me through what happens between pressing enter and my ETH arriving at my classmate's address."*

> **Honesty note:** the point of Week 1 is to remove the mystery. If any step felt like magic, ask AI to explain it until it doesn't — then write that understanding in `reflection.md`.
