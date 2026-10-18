# Track B local Arena dry-run evidence

**Status: local dry-run verified; course leaderboard evidence pending.**

- Wallet read by the adapter: `0xB03B27ea60D9fcc73366bd0ECB41945E91307209`.
- Network: Base Sepolia, chain ID 84532.
- Runner: repository `week-03/code/lab-bot/orchestrator.py`, one tick, `live=False`.
- Machine-readable runner output: [`dry_run_state.json`](dry_run_state.json).
- Result: bot `zhenzhenfang-liquidity-aware` loaded; PoolA and PoolB were read; the wallet's public address and tUSDC balance were read; strategy signal was HIT. The quoted gap was 8.83%, with modeled size 989 tUSDC and modeled two-leg net +62.930 tUSDC after the repository's fixed gas reserve. This is only a model, not realized profit or an executable atomic arbitrage.
- Execution: zero fires, no transaction hash, and no transaction receipt in this dry-run (`fires: 0`, `last_tx: null`). The prior successful RouterA swap is not assigned to this Arena run and was not inserted into its state.
- Screenshot: **PENDING**. The browser's security policy blocked access to `http://localhost:8010/dashboard.html` for screenshot verification. No substitute image was generated. The intended path, once captured manually from the actual page, is `screenshots/local_arena_dashboard_dry_run.png`.
- This is a **Local Arena Dashboard** run, not verified evidence from a course-wide leaderboard.

## Strategy summary

The strategy compares MAX/tUSDC reserve prices in PoolA and PoolB and chooses the lower-priced pool to buy from and the higher-priced pool to sell into. It estimates both legs with integer constant-product math, includes the modeled 0.30% fee on each leg, and applies a minimum-reserve filter. It caps the modeled input by a fixed maximum, a fraction of the cheaper pool's tUSDC reserve, and the wallet's observed tUSDC balance. Its displayed net estimate subtracts a fixed gas reserve because the repository has no tUSDC gas oracle; the estimate is not a profit guarantee. The adapter is read-only and refuses `fire()`, so it cannot send a transaction.

## Reproduce the one-tick dry-run

From the repository root, with `web3` installed:

```sh
env -u AGENT_KEY -u PRIVATE_KEY -u COURSE_TEST_SWAP_AUTHORIZED \
  -u ALLOW_UNLIMITED_ALLOWANCE_CONFIRMED \
  PYTHONDONTWRITEBYTECODE=1 python3 submissions/zhenzhenfang-source/run_local_dry_run.py
```

The command reads the public RPC and the fixed public wallet address only. It writes the fresh runner state to `dry_run_state.json`; it does not read a signer key, sign, or broadcast.
