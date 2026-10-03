---
name: treasury-swap
description: Swap tokens from the class wallet on Base Sepolia through the course RouterA, with a fresh quote, slippage protection, exact approval and on-chain verification. Use when the boss asks to swap, buy or sell a course token.
---

# Treasury swap (course RouterA)

Wallet and addresses: see **Treasury** in USER.md. Default wallet is the class wallet.

## RouterA has a NON-standard signature

```
swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address tokenIn, address tokenOut, address to)
```

Five arguments, **no `path` array** — this is not Uniswap V2's signature. ABI + addresses: the Week-3 agents `chain.py`. Pairs are Uniswap-V2-style (`getReserves`, `token0`, `token1`), fee 0.3%.

## Procedure

1. **Quote from live reserves** (never from memory — pools change): read `getReserves` and `token0` at the current block.
   `out = r_out * amtIn * 997 / (r_in * 1000 + amtIn * 997)`
2. Report to the boss: expected out, price impact (with and without fee), proposed `amountOutMin` (default 0.5% below the quote), and the wallet address. **Wait for `confirm`.**
3. If the wallet lacks `tokenIn` and the token is public-mint, mint exactly the amount needed.
4. Approve RouterA for **exactly** `amtIn`.
5. Execute; require receipt `status == 1`.
6. Verify with the Transfer event logs and a second RPC: actual amount received, allowance back to 0.
7. Report: quote vs actual, tx hashes.

## Stop conditions
- Receipt status 0, or received < `amountOutMin` → stop and report.
- The target pool has no min-output protection → stop; the boss decides per round.
