# Week 1 · Setup + Hands-On (your in-class guide)

> **This is the one document we use in class.** Part A gets your environment working (~20 min). Part B is the hands-on loop we do together: make a wallet → read the real chain → get test ETH → send to a classmate. **Testnet only — you never touch real money.**
>
> **If any command fails, paste the full command + full error into Claude Code and ask "how do I fix this on my OS?"** That's the method in this course, not cheating.

**You need:** a laptop (macOS / Windows / Linux), a browser, and a GitHub account.

### 🪟 Windows / 🍎 macOS / 🐧 Linux — read your icon

The **only** real difference is **which terminal you open** and **how you set a variable**:

- **🍎 macOS / 🐧 Linux:** open **Terminal**.
- **🪟 Windows:** open **"Anaconda Prompt"** from the Start menu (after Part A · Step 1) — **not** PowerShell or CMD.

| | 🍎 macOS / Linux (one line) | 🪟 Windows (cmd / Anaconda Prompt) |
|---|---|---|
| set a variable + run | `ADDR=0xABC python check_balance.py` | `set ADDR=0xABC`  ⏎  `python check_balance.py` |
| clear a variable | `unset ADDR` | `set ADDR=` |

> **🪟 Windows golden rule: NO space after `=`.** `set ADDR= 0xABC` stores a leading space and fails. Write `set ADDR=0xABC`.

---

# Part A — Install (first ~20 min)

| # | Step | Done when… |
|---|------|-----------|
| 1 | Install **Miniconda** | `conda --version` prints a version |
| 2 | Create the env (**Python 3.11**) | your prompt shows `(ai_finance)` |
| 3 | Install **web3** | `python -c "import web3"` gives no error |
| 4 | Get this **repo's code** | you can `cd` into `week-01/code` |

## Step 1 — Install Miniconda (one time)

Miniconda gives every student the **same Python**, isolated from your machine. Biggest "don't crash" move. Download the **Miniconda** installer, run it with **all defaults**: https://www.anaconda.com/download/success

- **🍎 macOS:** pick your chip (**Apple Silicon** for M1/M2/M3/M4, else **Intel**). Then open **Terminal**.
- **🪟 Windows:** run the `.exe`, keep defaults. Then open **Anaconda Prompt**.
- **🐧 Linux:** run the `.sh`, open a new terminal.

```bash
conda --version
```

> 🪟 "not recognized" → open **Anaconda Prompt**, not PowerShell. 🍎🐧 "command not found" → close & reopen the terminal once.

## Step 2 — Create the course environment

```bash
conda create -n ai_finance python=3.11 -y
conda activate ai_finance
python --version      # -> Python 3.11.x
```

> Prompt must show **`(ai_finance)`**. **Every new terminal: run `conda activate ai_finance` first.**
> Why 3.11: some libraries have no installer yet for 3.13/3.14 — 3.11 just works.

## Step 3 — Install the library

```bash
pip install web3 eth-account
python -c "import web3, eth_account; print('web3', web3.__version__)"
```

## Step 4 — Get this repo's code

```bash
git clone https://github.com/aaron-recompile/AI_Finance.git
cd AI_Finance/week-01/code
```

> 🪟 No Git? On the GitHub page click **Code → Download ZIP**, unzip, then `cd` into `...\week-01\code`.
> List the files to confirm: `ls` (🍎🐧) / `dir` (🪟) — you should see `read_chain.py`, `gen_wallet.py`, …

---

# Part B — Hands-on: the class "water cycle"

> Run everything below inside `week-01/code`, with your prompt showing `(ai_finance)`.

## 1. Make your wallet (everyone)

```bash
python gen_wallet.py
```

Prints an **ADDRESS** (public) and a **PRIVATE KEY** (secret).

- ✅ **Paste ONLY your ADDRESS** into class chat. 🚫 **Never paste the private key.**
- Throwaway learning key — never real money. *Keep it handy; Step 4 (sending) needs it.*

## 2. Read the real chain (everyone)

```bash
python read_chain.py
```

Expect the latest **block / gas** and vitalik.eth's **ETH + USDC** on **Ethereum mainnet (chainId 1)**. *No account, no money, no node — the chain is public, objective state.*

> ⚠️ Says **chainId 84532** or errors on USDC? You have a leftover `RPC` var → `unset RPC` (🍎) / `set RPC=` (🪟), rerun.

## 3. Instructor funds everyone (teacher)

Teacher collects all student addresses into `students.txt` (one per line), then from the course root:

```bash
set -a && source .env.faucet && set +a
AMOUNT_ETH=0.001 python weeks/week-01/code/faucet_distribute.py students.txt
```

## 4. Check it arrived (everyone)

```bash
# 🍎 macOS/Linux
ADDR=0xYourAddress python check_balance.py
# 🪟 Windows
set ADDR=0xYourAddress
python check_balance.py
```

Expect `ETH (native) : 0.001 ETH`. Or verify in a browser (no install):
`https://sepolia.basescan.org/address/0xYourAddress` (if it looks broken/unstyled, use `https://base-sepolia.blockscout.com/address/0xYourAddress`).

## 5. Send to a classmate (everyone)

Get a classmate's **address** from chat. You sign with **your own** key:

```bash
# 🍎 macOS/Linux (one line)
RPC=https://base-sepolia-rpc.publicnode.com PRIVATE_KEY=0xYOURkey TO=0xCLASSMATE AMOUNT_ETH=0.0002 python send_asset.py
```
```bat
:: 🪟 Windows (no space after =)
set RPC=https://base-sepolia-rpc.publicnode.com
set PRIVATE_KEY=0xYOURkey
set TO=0xCLASSMATE
set AMOUNT_ETH=0.0002
python send_asset.py
```

Watch the full life of a transaction: `assemble → sign → broadcast → mined`, balances move.
`PRIVATE_KEY` = **yours** (secret); `TO` = classmate's **address** (public). Your 0.001 covers gas.

## 6. Verify the transfer (both sides)

Re-run Step 4 (`check_balance.py` / explorer) for **both** addresses.

## 7. Feel contracts calling contracts (demos)

Open in a browser (double-click, no install):
- `../demos/vending-machine-callable.html` — a person and another contract call the same `buy()`.
- `../demos/composability-playground.html` — a swap cascading Wallet → AMM → Token.

## After class — reclaim (teacher)

```bash
set -a && source .env.faucet && set +a
python weeks/week-01/code/reclaim.py group-keys.txt      # sweep test ETH back to the funder
```

---

## When something breaks — the usual suspects

| Symptom | Cause → fix |
|---------|-------------|
| `conda: command not found` / "not recognized" | 🪟 use **Anaconda Prompt**; 🍎🐧 close & reopen the terminal. |
| `externally-managed-environment` / pip refuses | Forgot `conda activate ai_finance` — prompt must show `(ai_finance)`. |
| `ModuleNotFoundError: web3` | Wrong Python → `conda activate ai_finance`, redo Part A Step 3. |
| package won't install (mentions 3.13/3.14) | Wrong Python → recreate env with `python=3.11` (Part A Step 2). |
| `'RPC' is not recognized...` (🪟) | You used the Mac one-line style. On Windows use `set VAR=value` on its own line. |
| address error `Got: ' 0x..'` (🪟) | Space after `=` in `set`. Write `set ADDR=0x..` (no space). |
| `Network: ... chainId 84532` when you wanted mainnet | Leftover `RPC` → `unset RPC` / `set RPC=`. |
| basescan looks broken / unstyled | Ad-blocker stripped its CSS → whitelist it, use Incognito, or use Blockscout. |

## Not today (so we don't crash on day one)

- **Foundry (`forge`/`cast`/`anvil`)** → Week 2, when we write Solidity.
- **MetaMask** → optional; instructor demos it. Your wallet is the keypair from `gen_wallet.py`.
- **Getting testnet ETH** → we do it together in class from a browser faucet.
