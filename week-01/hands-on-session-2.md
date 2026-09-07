# Session 2 · Hands-On: Make Your Own Coin

> Continues Session 1. Today: **issue your own token, move it, and see it on the chain — all by code.**
> Slides: `slides/AI_Finance_Week1_Session2.html`. Scripts: `code/issue_asset.py`, `code/transfer_token.py`, `code/issue_asset_basesepolia.py`.
> **Testnet / local only — never real money.**

## Mental model (the one idea)
A token is **a table inside a contract** (`balanceOf[address] → amount`). "Issuing" = deploy that contract + write the first balances. **Transferring a token = the contract changes two rows; no ETH moves.**

## 0 · Get the latest code + activate your env
```bash
cd AI_Finance && git pull            # pull the Session 2 scripts (first time: git clone …)
source ~/ai_finance/bin/activate     # 🪟 Windows: ai_finance\Scripts\activate  — prompt shows (ai_finance)
cd week-01/code
```

---

## Path A — Local chain (everyone, free, instant)

**1) Start a local chain** (Terminal A, leave running)
```bash
anvil
```
**2) Issue your own coin** (Terminal B) — use your own name
```bash
NAME="Your Coin" SYMBOL=YOU SUPPLY=1000000 python issue_asset.py
```
Copy the printed `deployed at: 0x…`.

**3) Transfer some to a classmate**
```bash
TOKEN=0xTHAT_ADDRESS TO=0xCLASSMATE AMOUNT=250 python transfer_token.py
```
You'll see your balance go down, theirs go up (`status success`). That's the contract editing two rows — **ETH never moved.**

> Restart anvil → the chain wipes and your token address is gone. Just re-issue. It's a sandbox: break it freely.

---

## Path B — Real testnet, Base Sepolia (optional / for keeps)

Puts your coin on a **public** chain anyone can view. Costs a little test ETH for gas, so use **your own wallet + your own test ETH** (from Session 1).

**1) Issue your coin on Base Sepolia** (pass YOUR private key)
```bash
PRIVATE_KEY=0xYOUR_KEY NAME="Your Coin" SYMBOL=YOU SUPPLY=100000 python issue_asset_basesepolia.py
```
It prints your contract address + a BaseScan link.

**2) Send some of your coin to the instructor**
```bash
RPC=https://base-sepolia-rpc.publicnode.com \
PRIVATE_KEY=0xYOUR_KEY \
TOKEN=0xYOUR_COIN_ADDRESS \
TO=0xINSTRUCTOR_ADDRESS \
AMOUNT=1000 python transfer_token.py
```
Three addresses, don't mix them up: `PRIVATE_KEY` = yours · `TOKEN` = **your own** coin's contract · `TO` = the instructor's address.

**3) Verify in a browser** (no install)
```
https://base-sepolia.blockscout.com/token/0xYOUR_COIN_ADDRESS
```
See your symbol, total supply, and holders. The instructor's address now holds your coin too.

> Optional GUI: you can also do the **transfer** in MetaMask (Import account with your key → add Base Sepolia → Import token by contract address → Send). MetaMask can move a token but **cannot issue one** — that still needs the code above.

---

## Read vs Write (used every week after)
- **Read** = `.functions.balanceOf(x).call()` → ask only, free, no transaction.
- **Write** = build → sign → send → wait for receipt → costs gas, changes state.
- MetaMask's "Confirm" is just those write steps behind a button.

## If something breaks
| Symptom | Fix |
|---|---|
| `cannot connect to localhost:8545` | `anvil` isn't running → start it in Terminal A |
| `transfer` reads balance 0 / reverts | anvil restarted (chain wiped) → re-run `issue_asset.py` |
| no `(ai_finance)` / `ModuleNotFoundError` | activate the env |
| `issue_asset_basesepolia.py: No key` | pass `PRIVATE_KEY=0x…` (your own) |
| file not found | `git pull` — you don't have the Session 2 scripts yet |
| `0 ETH on Base Sepolia` | out of gas → fall back to Path A (anvil), or ask the instructor |
