# Track B local Arena dry-run evidence

**Status: local dry-run and one local LIVE swap receipt verified; course leaderboard evidence pending.**

- Wallet read by the adapter: `0xB03B27ea60D9fcc73366bd0ECB41945E91307209`.
- Network: Base Sepolia, chain ID 84532.
- Runner: repository `week-03/code/lab-bot/orchestrator.py`, one tick, `live=False`.
- Machine-readable runner output: [`dry_run_state.json`](dry_run_state.json).
- Result: bot `zhenzhenfang-liquidity-aware` loaded; PoolA and PoolB were read; the wallet's public address and tUSDC balance were read; strategy signal was HIT. The quoted gap was 8.83%, with modeled size 989 tUSDC and modeled two-leg net +62.930 tUSDC after the repository's fixed gas reserve. This is only a model, not realized profit or an executable atomic arbitrage.
- Dry-run execution: zero fires and no transaction hash or receipt in the dry-run (`fires: 0`, `last_tx: null`). A separate LIVE runner outcome was later recorded as unknown and then independently verified against Base Sepolia RPC; details are below.
- Screenshot: **PENDING**. The browser's security policy blocked access to `http://localhost:8010/dashboard.html` for screenshot verification. No substitute image was generated. The intended path, once captured manually from the actual page, is `screenshots/local_arena_dashboard_dry_run.png`.
- This is a **Local Arena Dashboard** run, not verified evidence from a course-wide leaderboard.

## Strategy summary

The strategy compares MAX/tUSDC reserve prices in PoolA and PoolB and chooses the lower-priced pool to buy from and the higher-priced pool to sell into. It estimates both legs with integer constant-product math, includes the modeled 0.30% fee on each leg, and applies a minimum-reserve filter. It caps the modeled input by a fixed maximum, a fraction of the cheaper pool's tUSDC reserve, and the wallet's observed tUSDC balance. Its displayed net estimate subtracts a fixed gas reserve because the repository has no tUSDC gas oracle; the estimate is not a profit guarantee.

## Arena LIVE adapter implementation status

The adapter contains a guarded one-shot LIVE path. It can send only from a `fire()` call made during the repository orchestrator LIVE tick. `run_local_live_once.py` reads a signer through hidden terminal input, validates its derived address against the fixed wallet, and keeps it process-local. The runner refuses to proceed unless `COURSE_TEST_SWAP_AUTHORIZED=YES` is already set; it never sets that gate. The adapter also requires an explicit unlimited-allowance acknowledgement when the allowance is `uint256` max, never approves, uses an explicit signer, and sends with one attempt.

Execution is exactly one 1 tUSDC -> MAX **single-leg swap** using a positive `amountOutMin`, a 1% quote tolerance, gas estimation and an 800,000 gas hard cap, and receipt/calldata/Transfer-event verification. It does not perform the second pool leg, does not claim arbitrage profit, and records zero P&L for this validation action. Only a receipt-verified result increments successful `fires` and updates `last_tx`; unverified results remain unknown and are not counted.

## Independently verified LIVE transaction

- Transaction: [`0x033fcad2e3b1e2afbeeb92e150ace817aa03551cc6350f2aefa909a86b412069`](https://sepolia.basescan.org/tx/0x033fcad2e3b1e2afbeeb92e150ace817aa03551cc6350f2aefa909a86b412069).
- Base Sepolia RPC read: chain ID 84532; receipt status 1; block 48269151; gas used 96180.
- Sender: `0xB03B27ea60D9fcc73366bd0ECB41945E91307209`; router: `0x2fc7C313bf38f0af4D92E8bE7347500D39174b82`.
- Decoded calldata specifies 1 tUSDC input, `amountOutMin` 1541269716689068 MAX base units (0.001541269716689068 MAX), the configured tUSDC and MAX contracts, and the sender as recipient.
- Receipt Transfer logs show exactly 1000000000000000000 tUSDC (1 tUSDC) leaving the wallet for PoolA and 1556838097665726 MAX (0.001556838097665726 MAX) received by the wallet. This verifies a **ONE-LEG TEST SWAP**, not a **TWO-POOL ARBITRAGE**.
- The runner's original verification failed because Web3 returned transaction input as bytes whose `.hex()` omitted the `0x` prefix, while locally encoded calldata included `0x`. The comparison therefore rejected identical calldata. Hash formatting had the same prefix issue. The adapter now normalizes bytes and hex strings before comparisons and persists canonical `0x`-prefixed hashes. Mock coverage checks byte-form calldata success and ensures unverified Transfer data remains unknown.
- The transaction hash was already present as `outcome_tx` in the runner's `live_state.json`; after independent RPC verification, the state now records one receipt-verified fire and this transaction as `last_tx`. The local Dashboard can display it. This does not prove course leaderboard attribution; that remains pending.

The dashboard helper now accepts `--mode dry-run` or `--mode live`. LIVE mode reads `live_state.json` only, checks that its JSON mode is exactly `LIVE`, and refuses missing or mismatched state without falling back to dry-run data. The dashboard labels unconfirmed outcomes separately from verified successful fires. This remains a **local dashboard**, not verified course leaderboard evidence.

## Reproduce the one-tick dry-run

From the repository root, with `web3` installed:

```sh
env -u AGENT_KEY -u PRIVATE_KEY -u COURSE_TEST_SWAP_AUTHORIZED \
  -u ALLOW_UNLIMITED_ALLOWANCE_CONFIRMED \
PYTHONDONTWRITEBYTECODE=1 python3 submissions/midterm/zhenzhenfang-source/run_local_dry_run.py
```

The command reads the public RPC and the fixed public wallet address only. It writes the fresh runner state to `dry_run_state.json`; it does not read a signer key, sign, or broadcast.

To open the dashboard against that captured dry-run state, run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 submissions/midterm/zhenzhenfang-source/serve_local_dashboard.py --mode dry-run
```

Then open `http://localhost:8010/dashboard.html`. The helper serves a copy of the repository dashboard with the actual dry-run state from this folder; it does not add a prior transaction to the dashboard. Stop the local server with Ctrl-C. Capture the actual page to `screenshots/local_arena_dashboard_dry_run.png` manually; that screenshot is still pending in this checkout.

The independently verified LIVE snapshot is included as `live_state.json`. To open it, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 submissions/midterm/zhenzhenfang-source/serve_local_dashboard.py --mode live
```

This reads `submissions/midterm/zhenzhenfang-source/live_state.json` and will fail if the file is missing or does not declare `mode: LIVE`. The dashboard HTML is copied into this submission directory, and the helper validates the selected state before serving it. The displayed state is a snapshot taken when the dashboard server starts; restart the server to refresh it. The course has not confirmed that this local dashboard qualifies as its leaderboard.
