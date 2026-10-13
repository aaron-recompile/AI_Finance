





















































































çcd ~/AI_Finance/AI_Finance && git status --short
# Liquidity-Aware DEX Spread Monitor

## Strategy
This strategy monitors the MAX/tUSDC spot prices on PoolA and PoolB.
It calculates the relative price spread between the two pools and checks
whether both pools meet a minimum tUSDC reserve threshold.

## Signal Rules
- Calculate each quoted price as tUSDC reserve divided by MAX reserve.
- Calculate the relative spread as higher price / lower price - 1.
- Signal HIT only when the spread is at least 1% and both pools have at
  least 1,000 tUSDC in reserves.
- Otherwise, return SKIP.

## Initial Test
The initial dry-run reported approximately:
- PoolA: 1,903.09 tUSDC per MAX
- PoolB: 1,916.95 tUSDC per MAX
- Relative spread: 0.73%
- Signal: SKIP

## Risk Controls and Limitations
This version is a read-only monitor. It does not execute trades.
The reserve-based price comparison does not account for actual trade size,
swap fees, slippage, gas costs, or transaction failure risk.
A signal is not a guarantee of profit. Live execution requires separate
implementation, testing, and review.
