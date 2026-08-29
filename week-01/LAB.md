# Week 1 · Hands-On Lab — the class "water cycle"

> One full loop of *touching* the chain: make a wallet → read the real chain → get test ETH → check it → send to a classmate → verify. **Testnet only — never real money.** Every command is given for **🍎 macOS/Linux** and **🪟 Windows**; they differ only in how you set variables.

**Before you start:** finish [`SETUP.md`](../SETUP.md) once (Miniconda + `conda activate ai_finance` + `pip install web3 eth-account` + clone). Then, in every new terminal:

```bash
conda activate ai_finance      # your prompt must show (ai_finance)
cd AI_Finance/week-01/code     # 🪟 Windows: cd AI_Finance\week-01\code
```

### 🍎 vs 🪟 — how to pass a variable to a script

| | 🍎 macOS / Linux (one line) | 🪟 Windows cmd / Anaconda Prompt |
|---|---|---|
| set + run | `ADDR=0xABC python check_balance.py` | `set ADDR=0xABC`  ⏎  `python check_balance.py` |
| clear one | `unset ADDR` | `set ADDR=` |

> **🪟 Windows golden rule: NO space after `=`.** `set ADDR= 0xABC` stores a leading space and the address fails. Write `set ADDR=0xABC`.

---

## Step 1 — Make your wallet (everyone)

```bash
python gen_wallet.py
```

Prints an **ADDRESS** (public) and a **PRIVATE KEY** (secret).

- ✅ **Paste ONLY your ADDRESS** into the class chat.
- 🚫 **Never paste the private key** anywhere. It *is* the wallet.
- This is a throwaway learning key — never put real money behind it.

*Keep this terminal / note your key somewhere private; Step 5 (sending) needs it.*

---

## Step 2 — Read the real chain (everyone)

Prove the chain is public, objective state — no account, no money, no node:

```bash
python read_chain.py
```

Expect: latest **block number**, **gas price**, and vitalik.eth's **ETH + USDC** on **Ethereum mainnet (chainId 1)**.

> ⚠️ If it says a different chain (e.g. **chainId 84532**) or errors on USDC, you have a leftover `RPC` variable. Clear it and rerun:
> `unset RPC` (🍎) / `set RPC=` (🪟).

---

## Step 3 — Instructor funds everyone (teacher only)

Teacher collects all student addresses into `students.txt` (one per line), then from the `course/` folder:

```bash
set -a && source .env.faucet && set +a          # loads FUNDER_KEY (teacher wallet)
AMOUNT_ETH=0.001 python weeks/week-01/code/faucet_distribute.py students.txt
```

Sends 0.001 test ETH to each address on **Base Sepolia**. Invalid/duplicate lines are skipped; it refuses to run on mainnet.

---

## Step 4 — Check your test ETH arrived (everyone)

**By code:**

```bash
# 🍎 macOS/Linux
ADDR=0xYourAddress python check_balance.py
# 🪟 Windows
set ADDR=0xYourAddress
python check_balance.py
```

Expect `ETH (native) : 0.001 ETH` on **Base Sepolia**. (`check_balance.py` defaults to Base Sepolia and never crashes on the wrong chain.)

**By browser (no install):** paste your address after the explorer URL —

```
https://sepolia.basescan.org/address/0xYourAddress
```

See your **Balance** and the incoming transaction from the teacher. (If basescan renders unstyled/blank, use `https://base-sepolia.blockscout.com/address/0xYourAddress`.)

---

## Step 5 — Send to a classmate (everyone)

Get a classmate's **address** from chat. You sign with **your own** private key:

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

Watch the full life of a transaction: `assemble → sign → broadcast → mined`, and the before/after balances move.

- `PRIVATE_KEY` = **yours** (secret). `TO` = classmate's **address** (public).
- You need a little test ETH for **gas** — the 0.001 from Step 3 covers it.

---

## Step 6 — Verify the transfer (both sides)

Re-run Step 4's `check_balance.py` (or the explorer) for **both** addresses: sender down by ~0.0002 + gas, receiver up by 0.0002.

---

## Step 7 — Feel a contract call other contracts (optional demos)

Open these in a browser (double-click; no install):

- `../demos/vending-machine-callable.html` — a human and another contract call the same `buy()`; coins in, item out, change back.
- `../demos/composability-playground.html` — a swap cascading Wallet → AMM → Token.

---

## After class — reclaim the test ETH (teacher only)

So the coins don't scatter and can be reused next class:

```bash
set -a && source .env.faucet && set +a
python weeks/week-01/code/reclaim.py group-keys.txt      # sweeps each wallet back to the funder
```

---

## The gotchas we actually hit (keep this handy)

| Symptom | Cause → fix |
|---------|-------------|
| `'RPC' is not recognized...` (🪟) | You used the Mac one-line style. On Windows use `set VAR=value` on its own line. |
| Address error `Got: ' 0x..'` (🪟) | Space after `=` in `set`. Write `set ADDR=0x..` (no space). |
| `Network: ... chainId 84532` when you wanted mainnet | Leftover `RPC` var. `unset RPC` / `set RPC=`. |
| `BadFunctionCallOutput` reading USDC | You're on a testnet but reading mainnet USDC — same leftover-`RPC` cause. |
| `ModuleNotFoundError: web3` | You forgot `conda activate ai_finance`. |
| basescan page looks broken / unstyled | Ad-blocker stripped its CSS → whitelist basescan, use Incognito, or use Blockscout. |
