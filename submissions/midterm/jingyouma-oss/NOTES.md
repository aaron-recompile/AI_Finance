# Mid-term strategy notes

**Name:** Jingyou Ma

**GitHub:** jingyouma-oss

**Wallet:** `0x9d11a25F6DD44E31c3aAe7d3A39Fa017e6BFf047`

## What my strategy does
My `risk-adjusted-yield` bot deploys idle tUSDC into either LendA or LendB. It scores each pool as `supply APR - 0.5% x utilization`, chooses the higher score, keeps 10% of wallet cash liquid, and caps each order at both 5,000 tUSDC and 5% of pool cash. Immediately before execution it scans again, then verifies that the wallet received lending shares after the transaction confirms.

## Why it should make money
Suppliers earn the pool's lending APR, but a high headline APR can coincide with high utilization and poor withdrawal liquidity. The utilization penalty favors a better balance of yield and liquidity rather than blindly chasing the largest APR. The reserve, liquidity cap, minimum score, minimum order, and five-minute cooldown reduce concentration, market-impact, and repeated-transaction risk.

## What would make it lose
The strategy can lose or become temporarily illiquid if a lending contract fails, borrowers default beyond the protocol's protection, utilization rises abruptly, or the pool's rate falls after deposit. RPC failure, gas shortages, stale reads, and transaction reverts can also prevent execution. Testnet tUSDC has no guaranteed real-world value, and the reported annual yield is an estimate rather than realized instant profit.

## Evidence
- Live Base Sepolia supply: 900 tUSDC deposited into LendA; 899.6575968997554 lending shares received.
- Transaction: https://sepolia.basescan.org/tx/0xfd816a1a2772c09d71936f63751b1da77059940f0ecc0020045e37887fda0247
- Block: `49859629`
- Post-transaction wallet balance: 100 tUSDC; LendA shares: 899.6575968997554.
- Leaderboard screenshot is included in the Classroom PDF. The dashboard records one fire and zero immediately realized P&L; approximately 3.47 tUSDC/year is expected interest at the execution-time APR, not realized profit.
