# Build Your Own Uniswap — Foundry Project (Week 2 flagship)

A minimal `x * y = k` automated market maker (AMM) that really deploys and really
swaps. Compare it with `amm.py` one directory up (the off-chain, pure-Python
intuition version) — same math, but here it lives on-chain as a smart contract.

## Files

| File | What it is |
|------|------------|
| `src/SimpleAMM.sol` | The AMM: add/remove liquidity, swap, 0.3% fee, LP shares, `x * y = k` |
| `src/MockERC20.sol` | A minimal teaching ERC-20 (freely mintable, used to seed the pool) |
| `test/SimpleAMM.t.sol` | Acceptance tests: initial price, `k` never decreases, slippage grows with trade size, LPs earn fees |
| `script/DeployAMM.s.sol` | Deploy to a testnet + seed initial liquidity |

## Run the tests (no network, no private key)

```bash
forge test -vv
```

Expected: **5 passed**. This is the baseline your assignment must keep green.

## Deploy to a testnet (Base Sepolia)

```bash
export PRIVATE_KEY=0xYourTestnetKey     # an account that holds some Base Sepolia gas
forge script script/DeployAMM.s.sol --rpc-url base-sepolia --broadcast
```

The `base-sepolia` RPC alias is defined in `foundry.toml`. The script prints the
`tETH`, `tUSDC`, and `AMM` addresses plus the initial price (should be `≈ 2000e18`).

To also verify the source on BaseScan (so the contract gets Read/Write tabs), add
`--verify` after setting `export BASESCAN_API_KEY=...`.

## Interact

```bash
export AMM=0x...                                             # the deployed pool
cast call $AMM "price0In1()(uint256)" --rpc-url base-sepolia  # read the price (free)
cast send $AMM "swap0For1(uint256)" 5000000000000000000 \
     --rpc-url base-sepolia --private-key $PRIVATE_KEY        # sell 5 tETH (state change)
cast call $AMM "price0In1()(uint256)" --rpc-url base-sepolia  # price moved
```

`cast call` is a free read (view); `cast send` is a real transaction that costs gas
and changes state. Selling tETH pushes its price down along the `x * y = k` curve —
that is slippage, live on-chain.

## Assignment

- **Core:** harden the add/remove-liquidity edge cases, add more tests, and turn
  slippage-vs-trade-size into a table.
- **Stretch:** deploy it and do one swap from code with web3.py (see the Week 2 lab).
- If the math feels opaque, go back to `amm.py` and the `x * y = k` derivation in the
  notes. The contract is just that one line, put on-chain.

## Dependencies

This project uses `forge-std`. If `lib/forge-std` is missing after cloning, run:

```bash
forge install foundry-rs/forge-std
```
