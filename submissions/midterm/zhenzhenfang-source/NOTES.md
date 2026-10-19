# Midterm Track B — Liquidity-Aware MAX/tUSDC Strategy

## Strategy and expected return conditions

The original strategy reads PoolA and PoolB reserves, verifies each pair contains MAX and tUSDC, and normalizes reserve order using `token0()`. It compares both reserve prices, then estimates buying MAX in the cheaper pool and selling it in the dearer pool with integer constant-product math. The estimate includes a modeled 30 bps fee on each leg, reserve-driven price impact, a 1,000 tUSDC minimum reserve in each pool, an input cap of the smaller of 5,000 tUSDC or 2% of the cheaper pool, a wallet-balance cap, a fixed 1 tUSDC gas reserve, and a 2 tUSDC minimum estimated net return.

The strategy could make money only if the spread remains large enough after both fees, price impact, gas, and execution delay, and if both legs can execute at suitable prices. The fee is modeled from the course AMM source; the Router interface does not expose a fee query, and the fixed gas reserve is not an on-chain gas-to-tUSDC conversion. The provided interfaces expose separate single-swap calls, not an atomic two-pool arbitrage, so executing one leg and later attempting the other can leave the wallet holding MAX after adverse price movement or a failed second leg. Other loss risks include stale reserves, fee assumptions that differ from deployment, slippage, gas costs, contract/router risk, and the previously owner-confirmed unlimited RouterA allowance.

## Arena integration and execution limits

`strategy.py` implements the pure `decide(view)` interface. `zhenzhenfang_strategy_adapter.py` reads market reserves and the designated wallet's public balance, calls that strategy, and exposes the orchestrator `scan()` / `fire()` adapter. `run_local_live_once.py` calls the local repository orchestrator once with `tick(live=True, n=1)`; its hidden-input signer must match the fixed wallet. The LIVE path requires the bot-specific process gate `COURSE_TEST_SWAP_AUTHORIZED=YES`, an existing allowance, the separate local acknowledgement for a uint256-max allowance, a fresh signal, Base Sepolia chain ID 84532, expected token decimals, sufficient balances, a positive `amountOutMin`, a 1% slippage cap, a gas estimate under the 800,000 limit, an exact interactive confirmation, one send attempt, and receipt/calldata/Transfer-event verification. It never auto-approves and must not fall back to a funder or ephemeral wallet.

`COURSE_TEST_SWAP_AUTHORIZED` is an implementation guard in this bot. It is not proof of course authorization. The owner separately confirmed that the existing unlimited RouterA tUSDC allowance was intentional and accepted its risk; that confirmation is not a claim that the allowance is safe. The LIVE transaction below is a one-leg test swap, not a two-pool arbitrage. The recorded Dashboard P&L is 0; no arbitrage profit or realized positive P&L is claimed.

## Verified transaction evidence

- Wallet: `0xB03B27ea60D9fcc73366bd0ECB41945E91307209`.
- Network: Base Sepolia, chain ID `84532`.
- Transaction: [`0x033fcad2e3b1e2afbeeb92e150ace817aa03551cc6350f2aefa909a86b412069`](https://sepolia.basescan.org/tx/0x033fcad2e3b1e2afbeeb92e150ace817aa03551cc6350f2aefa909a86b412069).
- Receipt: success (`status=1`), block `48269151`, gas used `96180`.
- Sender: the wallet above. RouterA: `0x2fc7C313bf38f0af4D92E8bE7347500D39174b82`.
- The transaction spent `1 tUSDC` and the receipt's ERC-20 Transfer events show `0.001556838097665726 MAX` received. The calldata's `amountOutMin` was `1541269716689068` MAX base units. This is a **ONE-LEG TEST SWAP**, not a **TWO-POOL ARBITRAGE**.
- The runner initially marked the outcome `unknown` because Web3 returned the transaction input as bytes whose `.hex()` omitted the `0x` prefix, while encoded calldata included the prefix. The adapter now normalizes both before comparison. If receipt or Transfer verification is not complete, the result remains `unknown` and is not counted as a successful fire.
- `live_state.json` records one receipt-verified fire, this transaction hash, and P&L `0`. It is a local orchestrator state snapshot, not evidence of course leaderboard attribution.
- No authentic course leaderboard URL or screenshot is included. The local Dashboard is not represented as the course leaderboard. The final course PDF is therefore still pending; the existing evidence-status PDF, if present, is a status report listing pending evidence, not the final submission.

## Files and reproduction

The submission directory includes the strategy, its adapter, the one-tick dry-run and LIVE launchers, the local dashboard helper, mock tests, and the verified LIVE state snapshot. The launcher files locate `week-03/code/lab-bot` from this submission directory; run the commands below from the repository root.

Run the offline/mock tests without contacting RPC or signing:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s submissions/midterm/zhenzhenfang-source -p 'test_*.py' -v
```

Run one read-only local Arena tick (requires the repository's configured RPC):

```sh
env -u AGENT_KEY -u PRIVATE_KEY -u COURSE_TEST_SWAP_AUTHORIZED \
  -u ALLOW_UNLIMITED_ALLOWANCE_CONFIRMED \
  PYTHONDONTWRITEBYTECODE=1 python3 \
  submissions/midterm/zhenzhenfang-source/run_local_dry_run.py
```

Serve the already-recorded LIVE snapshot in the local dashboard:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  submissions/midterm/zhenzhenfang-source/serve_local_dashboard.py --mode live
```

Open `http://localhost:8010/dashboard.html`. This is a local dashboard snapshot, not a verified course leaderboard. The dashboard helper refuses to substitute dry-run data for LIVE state and only displays a successful fire when the state marks its receipt as verified.

## Remaining course evidence

The repository's Track B instructions require the bot and `NOTES.md` under `submissions/midterm/<github-name>/` via a PR, plus a PDF submitted through Google Classroom containing the wallet, transaction hash(es), a leaderboard screenshot, and 3–5 strategy sentences. The local repository does not establish that its dashboard is the official course leaderboard or provide its URL/attribution rules. Obtain the official leaderboard entry or course instructions and capture an authentic screenshot; then build and visually inspect the final PDF. Do not label the local dashboard or a Basescan page as the course leaderboard.

`generate_final_submission_pdf.py` expects a JSON manifest with `wallet_address`, `chain_id`, 3–5 `strategy_sentences`, `offline_tests.command` and `offline_tests.result`, the instructor-provided `leaderboard_url`, a real `leaderboard_screenshot` image path, and a `transactions` array. Each transaction entry needs `hash`, `balances_before`, and `balances_after` with `tUSDC` and `MAX` values. The builder verifies the transaction receipt, sender, router call, token events, and balance deltas over the configured Base Sepolia RPC; it refuses a missing screenshot or unverified evidence. The official leaderboard URL/screenshot and a verified before/after balance record for the included transaction are not currently in this folder, so a final PDF cannot yet be truthfully generated.
