# Week 1 · Setup + Hands-On (your in-class guide)

> **This is the one document we use in class.** Part A gets your environment working (~20 min). Part B is the hands-on loop we do together: make a wallet → read the real chain → get test ETH → send to a classmate. **Testnet only — you never touch real money.**
>
> **If any command fails, paste the full command + full error into Claude Code and ask "how do I fix this on my OS?"** That's the method in this course, not cheating.

**You need:** a laptop (macOS / Windows / Linux), a browser, and a GitHub account.

### 🪟 Windows / 🍎 macOS / 🐧 Linux — read your icon

The **only** real difference is **which terminal you open** and **how you set a variable**:

- **🍎 macOS / 🐧 Linux:** open **Terminal**.
- **🪟 Windows:** open **Command Prompt** (press Start, type **`cmd`**, hit Enter) — **not** PowerShell.

| | 🍎 macOS / Linux (one line) | 🪟 Windows (Command Prompt) |
|---|---|---|
| set a variable + run | `ADDR=0xABC python check_balance.py` | `set ADDR=0xABC`  ⏎  `python check_balance.py` |
| clear a variable | `unset ADDR` | `set ADDR=` |

> **🪟 Windows golden rule: NO space after `=`.** `set ADDR= 0xABC` stores a leading space and fails. Write `set ADDR=0xABC`.

---

# Part A — Install (first ~20 min)

| # | Step | Done when… |
|---|------|-----------|
| 1 | Install **Python 3.11** | `python --version` (🪟) / `python3.11 --version` (🍎🐧) prints `3.11.x` |
| 2 | Create + activate a **venv** | your prompt shows `(ai_finance)` |
| 3 | Install **web3** | `python -c "import web3"` gives no error |
| 4 | Get this **repo's code** | you can `cd` into `week-01/code` |

## Step 1 — Install Python 3.11 (one time)

We pin **Python 3.11** so everyone runs the same version (some libraries have no installer yet for 3.13/3.14 — 3.11 just works).

**Download page:** https://www.python.org/downloads/release/python-3110/ → scroll to the **"Files"** table at the bottom.

### 🪟 Windows

1. Download **"Windows installer (64-bit)"**.
2. Double-click it. On the first screen, **tick ✅ "Add python.exe to PATH"** (bottom of the window) — this is the one box that matters → click **Install Now** → **Close**.
3. Open **Command Prompt** (Start → type `cmd` → Enter) and verify:
   ```bat
   python --version      :: -> Python 3.11.x
   ```
   > "not recognized"? The PATH box wasn't ticked — re-run the installer, choose **Modify**, tick **"Add to environment variables"**, finish, then open a **fresh** Command Prompt.

### 🍎 macOS

1. Download **"macOS 64-bit universal2 installer"** (the `.pkg`).
2. Double-click → **Continue** → **Agree** → **Install** (enter your Mac password if asked) → **Close**.
3. Open the **Terminal** app (Cmd-Space, type "Terminal") and verify:
   ```bash
   python3.11 --version      # -> Python 3.11.x
   ```

### 🐧 Linux

```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv
python3.11 --version
```

## Step 2 — Create + activate the course environment (venv)

A **venv** is a private Python folder for this course — installs stay isolated from the rest of your machine. We name it `ai_finance`.

**Run this from the folder where you'll keep the course** (e.g. your home folder or Documents).

```bash
# 🍎 macOS / 🐧 Linux
python3.11 -m venv ai_finance
source ai_finance/bin/activate
python --version            # -> Python 3.11.x
```
```bat
:: 🪟 Windows (Command Prompt)
py -3.11 -m venv ai_finance
ai_finance\Scripts\activate
python --version
```

> Prompt must now show **`(ai_finance)`** at the start of the line.
> **Every new terminal: activate first** — `source ai_finance/bin/activate` (🍎🐧) / `ai_finance\Scripts\activate` (🪟). No `(ai_finance)` = wrong environment.

<details>
<summary><b>Already have conda? (optional alternative)</b></summary>

If you already use Anaconda/Miniconda and prefer it, you can skip the venv and use a conda env instead — everything downstream is identical (it also shows `(ai_finance)`):

```bash
conda create -n ai_finance python=3.11 -y
conda activate ai_finance
```
You do **not** need conda for this course; the venv above is the default path.
</details>

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
| `python: command not found` / "not recognized" | 🪟 re-run the installer and tick **"Add python.exe to PATH"**, open a fresh Command Prompt; 🍎🐧 use `python3.11`. |
| prompt has no `(ai_finance)` | You didn't activate → `source ai_finance/bin/activate` (🍎🐧) / `ai_finance\Scripts\activate` (🪟). |
| `externally-managed-environment` / pip refuses | Not in the venv — activate it first; prompt must show `(ai_finance)`. |
| `ModuleNotFoundError: web3` | Wrong Python → activate the venv, redo Part A Step 3. |
| package won't install (mentions 3.13/3.14) | Wrong Python → recreate the venv with **3.11** (Part A Step 2). |
| `py -3.11` not found (🪟) | Python 3.11 not installed or PATH box unticked → redo Part A Step 1. |
| `'RPC' is not recognized...` (🪟) | You used the Mac one-line style. On Windows use `set VAR=value` on its own line. |
| address error `Got: ' 0x..'` (🪟) | Space after `=` in `set`. Write `set ADDR=0x..` (no space). |
| `Network: ... chainId 84532` when you wanted mainnet | Leftover `RPC` → `unset RPC` / `set RPC=`. |
| basescan looks broken / unstyled | Ad-blocker stripped its CSS → whitelist it, use Incognito, or use Blockscout. |

## Not today (so we don't crash on day one)

- **Foundry (`forge`/`cast`/`anvil`)** → Week 2, when we write Solidity.
- **MetaMask** → optional; instructor demos it. Your wallet is the keypair from `gen_wallet.py`.
- **Getting testnet ETH** → we do it together in class from a browser faucet.
