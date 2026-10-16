---
name: treasury-flash-arb
description: Run a flash-loan arbitrage between the course CHEAP and DEAR pools on Base Sepolia using the class wallet's own Arbitrageur contract (profit goes to the class wallet). Use when the boss asks about the flash-loan demo, the CHEAP/DEAR gap, or an arbitrage opportunity there.
---

# Treasury flash-loan arbitrage

Wallet and addresses: see **Treasury** in USER.md.

## Contracts
- **Use only the class wallet's OWN Arbitrageur** (owner = class wallet) — the profit returns to you.
- A "course copy" exists whose owner is the funder: anyone can call `run()`, but the **profit goes to ITS owner**, not you. Never use that one.
  *(This is exactly the "pay yourself" idea from the Week-3 homework — the profit recipient is fixed in the contract.)*
- `run(uint256 borrowUsdc)`: borrow tUSDC from FlashLender → buy MAX on CHEAP → sell MAX on DEAR → repay principal + 0.05% fee → send the rest to the owner. One transaction; if the loan can't be repaid, the whole tx reverts.
- Source: `Arbitrageur.sol` (Week-3 flashloan-foundry). CHEAP / DEAR / FlashLender addresses: the Week-3 agents `chain.py`.

## Procedure
1. Read CHEAP and DEAR reserves at the current block. Size the borrow with the course arb formula (swap fee 0.3%, flash fee 0.05%).
2. Report: gap %, borrow amount, flash fee, expected profit in tUSDC, gas estimate in ETH (do not convert to USD without a verified rate), and the profit recipient. **Wait for `confirm`.**
3. Re-quote right before sending; if expected profit dropped materially, stop and report.
4. Call `run(borrow)` from the class wallet; require `status == 1`.
5. Verify from the tx's Transfer logs: borrow in, repay out (principal + fee), profit to the class wallet. Report tx hash and realized profit.

## Example (a real run)
Gap ~6% → borrow ~25,700 tUSDC → profit **~678 tUSDC** to the class wallet; gas ~0.0000064 ETH. Afterwards the gap closed to ~0.65%.

## After running
The CHEAP/DEAR gap is a **classroom demo**; after an arb it is closed. Reopening it needs the funder key and is the boss's action, not the agent's.

## Note
`run()` has no minimum-profit guard. A failed run costs gas.
