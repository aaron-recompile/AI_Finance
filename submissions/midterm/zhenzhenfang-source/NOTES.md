# Midterm Track B — Liquidity-Aware Strategy Bot

## Strategy
The bot monitors MAX/tUSDC prices in PoolA and PoolB.
It calculates the quoted price spread and checks the liquidity
available in both pools. It reports HIT when the spread is at
least 1% and both pools meet the minimum liquidity threshold.

## Rationale
Price differences between pools may create arbitrage opportunities.
Liquidity filters help avoid acting on pools with insufficient reserves.
However, quoted spreads do not guarantee profit after fees, slippage,
and gas costs.

## Current Status
The bot has been tested in dry-run mode and produced HIT signals.
Live trading is not implemented. No trade execution is claimed here.
