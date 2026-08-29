# Week 1 · First-Class Setup (do this in order)

> Goal for today: **run one line of Python that reads a live blockchain, and generate your own wallet.** That's it. We install only what Week 1 needs. (Solidity/Foundry comes in Week 2.)
>
> **If any command fails, don't panic — paste the full command + full error into Claude Code and ask "how do I fix this on my OS?"** That's the method in this course, not cheating. Everything is free and uses **testnets only — you never touch real money.**

**Time:** ~20 min. **You need:** a laptop (macOS / Windows / Linux), a browser, and a GitHub account.

### 🪟 Windows / 🍎 macOS / 🐧 Linux — read your icon

Look for the OS icons below. The **only** real difference is **which terminal you open**:

- **🍎 macOS / 🐧 Linux:** open the **Terminal** app.
- **🪟 Windows:** after Step 1, open **"Anaconda Prompt"** from the Start menu — **not** PowerShell or CMD. Run every command in Anaconda Prompt.

Once your terminal is open, **the commands are identical on all three systems.**

---

## The 5 steps at a glance

| # | Step | You're done when… |
|---|------|-------------------|
| 1 | Install **Miniconda** | `conda --version` prints a version |
| 2 | Create the course env (**Python 3.11**) | your prompt shows `(ai_finance)` |
| 3 | Install **web3** into it | `python -c "import web3"` prints nothing (no error) |
| 4 | Get this **repo's code** | you can `cd` into `week-01/code` |
| 5 | **Smoke test** | `read_chain.py` prints a block number; `gen_wallet.py` prints an address |

Do them **top to bottom.**

---

## Step 1 — Install Miniconda (one time)

Miniconda gives every student the **same Python**, isolated from whatever else is on your laptop. This is the single biggest "don't crash" move.

Download the **Miniconda** installer for your OS and run it with **all defaults**:
https://www.anaconda.com/download/success

- **🍎 macOS:** pick the installer matching your chip (**Apple Silicon** for M1/M2/M3/M4, **Intel** otherwise). Then open **Terminal**.
- **🪟 Windows:** run the `.exe`, keep defaults. Then open **Anaconda Prompt** from the Start menu.
- **🐧 Linux:** run the `.sh` installer, then open a new terminal.

Verify (in your terminal):

```bash
conda --version
```

> Prints `conda 24.x` (any version is fine) → Step 1 done.
> **🪟 Windows:** if it says "not recognized", make sure you opened **Anaconda Prompt**, not PowerShell.
> **🍎🐧 mac/Linux:** if "command not found", **close and reopen** the terminal once.

---

## Step 2 — Create the course environment

```bash
conda create -n ai_finance python=3.11 -y
conda activate ai_finance
```

Verify — your prompt should now start with **`(ai_finance)`**, and:

```bash
python --version      # -> Python 3.11.x
```

> **Why 3.11 (not the newest):** some libraries don't yet ship installers for Python 3.13/3.14, and you get a confusing error. 3.11 just works.
>
> **Every new terminal, run `conda activate ai_finance` first.** If your prompt doesn't say `(ai_finance)`, you're in the wrong Python.

---

## Step 3 — Install the Week 1 library

```bash
pip install web3 eth-account
```

Verify:

```bash
python -c "import web3, eth_account; print('web3', web3.__version__)"
```

> Prints e.g. `web3 7.16.0` → done. (Installing with `pip` *inside* the conda env is normal and correct.)

---

## Step 4 — Get this repo's code

You need **Git** for `clone`. macOS/Linux usually have it (`git --version`); **🪟 Windows:** if `git` is missing, either install "Git for Windows", or just use **Option B (ZIP)** below — no Git needed.

**Option A — git clone (recommended):**

```bash
git clone https://github.com/aaron-recompile/AI_Finance.git
cd AI_Finance/week-01/code
```

**Option B — no Git? download the ZIP:** on the GitHub repo page click **Code → Download ZIP**, unzip it, then in your terminal `cd` into the unzipped `.../week-01/code` folder.

Verify:

```bash
ls        # 🍎🐧 mac/Linux
dir       # 🪟 Windows
# you should see read_chain.py, gen_wallet.py, send_asset.py, ...
```

---

## Step 5 — Smoke test (the payoff)

Make sure your prompt says `(ai_finance)` and you're inside `week-01/code`, then:

```bash
# 1) READ a real blockchain (Ethereum mainnet, read-only, free, no account)
python read_chain.py

# 2) Generate YOUR OWN wallet (a keypair)
python gen_wallet.py
```

- `read_chain.py` should print the latest **block number**, **gas price**, and an address's ETH + USDC balance. *You just touched the live chain.*
- `gen_wallet.py` prints an **ADDRESS** (public) and a **PRIVATE KEY** (secret).
  - **Paste only the ADDRESS into class chat.** Never paste the private key anywhere.
  - This is a throwaway testnet key — **never put real money behind it.**

If both printed without a red error → **you're fully set up for Week 1.** 🎉

---

## If it breaks — the 4 usual suspects

| Error you see | Fix |
|---------------|-----|
| `conda: command not found` / "not recognized" | 🪟 use **Anaconda Prompt**; 🍎🐧 close & reopen the terminal. |
| `externally-managed-environment` / pip refuses | You forgot `conda activate ai_finance`. Prompt must show `(ai_finance)`. |
| `ModuleNotFoundError: No module named 'web3'` | Wrong Python. Run `conda activate ai_finance`, then re-run Step 3. |
| a package won't install (mentions 3.13/3.14) | You're on the wrong Python; recreate the env with `python=3.11` (Step 2). |

Still stuck? **Paste the full command + full error into Claude Code.** Or grab the instructor — there's a pre-funded backup wallet to keep you moving.

---

## Not today (so we don't crash on day one)

- **Foundry (`forge`/`cast`/`anvil`)** → Week 2, when we write Solidity. Skipping it now.
- **MetaMask** → optional; the instructor demos it. Your "wallet" is just the keypair from `gen_wallet.py`.
- **Getting testnet ETH** → we do this together in class from a browser faucet; nothing to pre-install.
