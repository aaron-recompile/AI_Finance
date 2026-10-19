# Midterm Track B — Inventory Rebalancer

## Wallet

0xB7a1e8AD312fe33433A3e6cA3DD62C79dA3ec554

## Strategy

My strategy is an inventory-aware DEX rebalancer. It reads the MAX/tUSDC prices on DEX-A and DEX-B and also checks the MAX and tUSDC balances in my own wallet. If my MAX exposure is too high, the bot sells MAX on the more expensive DEX; if my MAX exposure is too low, it buys MAX on the cheaper DEX. The bot only trades when the price gap between the two DEXs is large enough, and it uses a small fraction of the wallet balance for each trade to reduce market impact. The strategy is designed to improve execution price while keeping the portfolio closer to its target allocation.

## On-chain Transactions

1. 87f57ccc5e1102afa2b0804c01e9248eb1e02fd9e1a3640466f094d6c325f37f
2. fa3704ffc86e83299b23659d55181dd2191bc8dea278b4c9951a7c8a04bb5647
3. 70c73089341b9ebb448719070e8514490d884d878f77e13f23894aebbe11c479

## Arena Result

The strategy successfully ran in LIVE mode and appeared on the P&L leaderboard as `inventory-rebalancer`.

The leaderboard recorded real on-chain fires and a last transaction hash.

## Risk / Learning

During testing, larger trades caused noticeable price impact in the DEX pools. I therefore reduced the trade size to make the strategy more conservative and reduce repeated market impact.
