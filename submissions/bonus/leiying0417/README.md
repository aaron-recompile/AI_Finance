# AI Finance Homework Code - Leiying Wang

GitHub username: `leiying0417`

This folder collects the read-only research and simulation code from my AI Finance OpenClaw project. I used it to understand the class DEX pools on Base Sepolia and prepare a bounded test trade. I developed the project with AI assistance and reviewed its behavior through simulations, tests and transaction evidence.

## Files

| File | Purpose |
| --- | --- |
| `observe.py` | Reads token decimals, contract code, pool reserves and static quotes at a fixed block. Compares two hypothetical arbitrage directions. |
| `dex_arbitrage.py` | Checks Router/Factory/Pool relationships, compares arbitrage quotes, and simulates both legs in shared EVM state. Its research decision remains `WAIT`; it has no signer or broadcast path. |
| `max_once.py` | Prepares and simulates a single tUSDC-to-MAX purchase capped at 1 tUSDC, with finite allowance, minimum output and estimated fee checks. No live execution mode is available. |
| `reports/dex-arbitrage/RouterA-verified.json` | Public Router A contract-verification response retained by the original project. The planners compare its runtime bytecode against RPC results. This is a source artifact, not a transaction receipt. |
| `requirements.txt` | Direct Python dependencies. Web3 matches the project's recorded version. This is not a complete dependency lock file. |
| `.gitignore` | Excludes local environments, secrets, generated reports and downloaded course code. |

The three Python files are unchanged copies of my original project files. The included JSON is also unchanged. Live signers, recovery executors, private keys, wallet files and execution journals are not part of this submission.

## Setup for read-only reproduction

Use Python 3.11 and Git. Work from this folder:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p vendor
git clone --no-checkout https://github.com/aaron-recompile/AI_Finance.git vendor/AI_Finance
git -C vendor/AI_Finance checkout --detach 7c6d70921d03e7fbb9fdbfde84ff2cb570a29a3c
```

The pinned course checkout is necessary because `observe.py` parses public addresses from `week-03/code/lab-bot/chain.py` and `deployed.json`, and records the checkout's Git version. It does not import or run the course bots. Do not add the downloaded `vendor` folder to the PR. If that directory already exists, check it before cloning or changing it.

Run only the research programs:

```bash
.venv/bin/python observe.py
.venv/bin/python dex_arbitrage.py
.venv/bin/python max_once.py --dry-run
```

They make RPC reads and, where supported, simulations. They write local reports but do not sign or broadcast transactions. RPC availability, contract changes, simulation support and the fixed wallet's current state can cause a program to stop. `dex_arbitrage.py` intentionally returns `WAIT`; `max_once.py` also stops if the wallet already holds MAX or an execution intent exists. A simulation does not authorize execution.

For this submission, the three Python files passed a fresh syntax check and the JSON parsed successfully. No fresh network run or clean-environment dependency installation was performed while packaging these files. The original project's additional tests are not included here.

## What I learned

Small arbitrage quotes in my project were negative before gas costs, so the strategy waited. For a separate functional demonstration, I authorized one small purchase and the agent chose Pool A for its higher MAX quote. The actual swap spent 1 tUSDC and received 0.000569667394358786 MAX. This demonstrated a working testnet action, not profitable arbitrage. After an application validation error, read-only reconciliation confirmed success and execution stopped without another swap.

Public wallet: `0x3AF10AC46be1148ABADEe3C7168e27F960e0153d`

[Successful Base Sepolia swap on BaseScan](https://sepolia.basescan.org/tx/0xac2dcb833704fd10de22f64630e64f471f17e4db96f0747da65680c528b1eab1)

This code archive contains the preparation programs, not the live component that submitted that transaction. My main learning was to compare quotes, set explicit limits and verify blockchain evidence before taking another action.
