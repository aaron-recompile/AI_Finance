---
name: treasury-lend
description: Read or manage the class wallet's LendA borrow position on Base Sepolia (collateral, debt, health factor, liquidation price), compute remedies, and explain lend-watch alerts. Use when the boss asks about the loan, health factor, liquidation risk, or when a lend-watch alert fires.
---

# Treasury lending (course LendA)

Wallet and addresses: see **Treasury** in USER.md.

## The position
- Pool: LendA `<addr>` (ABI `LendingPool` in the Week-3 agents `chain.py`).
- Collateral MAX, debt tUSDC. Oracle: `price()` (course oracle, not DEX spot). Liquidation threshold (collateral factor) 0.75.
- **This position is the classroom demo. Keep it open. Never repay, add collateral, or borrow more without the boss's `confirm`.**

## Formulas (verify against `healthFactor()` every time)
- `HF = collateral * price * 0.75 / debt`
- liquidation price = `debt / (collateral * 0.75)`
- MAX to add to reach HF target T: `debt * T / (price * 0.75) - collateral`
- tUSDC to repay to reach T: `debt - collateral * price * 0.75 / T`
- Debt accrues interest, so the liquidation price slowly rises — say so when relevant.

Example: 1 MAX, 750 tUSDC, price 2000 → HF 2.0, liquidation price 1000. At price 1200 → HF 1.2; to reach HF 2: add 0.666667 MAX **or** repay 300 tUSDC.

## Monitoring (two layers)
- **Fast layer:** a no-LLM cron every 10 min runs a read-only `lend_watch` check; stays silent while HF ≥ 1.3.
- **Slow layer:** an LLM turn, woken only when the fast layer sees trouble; tools read/exec only.
- If waking the slow layer fails, the fast layer sends a raw alert straight to Telegram (no LLM) — so an alert never gets lost.

## When an alert fires
1. Re-read the chain; do not trust the saved snapshot alone.
2. Report HF, collateral, debt, oracle price, liquidation price, % downside left, and the two alternative remedies.
3. If you can tell *why* HF moved (oracle price change vs. interest), say it.
4. **Advice only. No automatic financial action.**
