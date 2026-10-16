# SimpleLend — Your Own On-Chain Pawnshop (lending + liquidation)

The Week 2 / Session 4 flagship contract. A sibling to `amm-foundry`: a minimal
lending market that **really deploys and really liquidates**. Compare it with
`../lend.py` (the off-chain, pure-Python intuition version) — same "health factor"
math, but here it lives on-chain as a smart contract.

## Files

| File | What it is |
|------|------------|
| `src/SimpleLend.sol` | The lending market: deposit/withdraw collateral, borrow/repay, health factor, liquidation |
| `src/MockERC20.sol` | A minimal teaching ERC-20 (freely mintable, used for WETH collateral and USDC debt) |
| `test/SimpleLend.t.sol` | Acceptance tests: HF math, over-borrow rejected, price drop makes it liquidatable, liquidation seizes collateral, healthy positions can't be liquidated |
| `script/DeployLend.s.sol` | Deploy to a chain + set up a starting position |

## What the contract teaches

- `deposit / withdraw` — put in / take out collateral (WETH).
- `borrow / repay` — take on / pay back debt (USDC). Both borrowing and withdrawing require **HF ≥ 1**.
- `healthFactor(user)` = collateral value × liquidation threshold (80%) ÷ debt. `>1` is safe, `<1` can be liquidated.
- `setPrice` — a **manual teaching oracle**, so in class you can "cut the ETH price on the spot" to manufacture a liquidation.
- `liquidate(user)` — when HF < 1, a liquidator repays the debt and seizes the collateral at a **110% discount** (that 10% is the liquidation bonus).

## Run the tests (no network, no private key)

```bash
export PATH="$HOME/.foundry/bin:$PATH"
forge test -vv
```

Expected: **5 passed** — HF on deposit/borrow, over-borrow rejected, price drop turns
the position liquidatable, liquidation seizes the collateral, and a healthy position
cannot be liquidated. This is the baseline your assignment must keep green.

## Deploy locally on anvil + manufacture a liquidation

```bash
# Terminal A: anvil (leave it running)
anvil

# Terminal B:
export PATH="$HOME/.foundry/bin:$PATH"
export PRIVATE_KEY=0xac0974...ff80   # Anvil test key #0 (public, local only)
forge script script/DeployLend.s.sol --rpc-url http://localhost:8545 --broadcast
# note the printed WETH / USDC / LEND addresses
```

Then use `cast` to walk through "open a position → cut the price → watch HF fall below 1":

```bash
L=<LEND address>;  W=<WETH address>;  RPC=http://localhost:8545

# deposit 1 WETH, borrow 1000 USDC
cast send $W "approve(address,uint256)" $L 1000000000000000000 --rpc-url $RPC --private-key $PRIVATE_KEY
cast send $L "deposit(uint256)" 1000000000000000000            --rpc-url $RPC --private-key $PRIVATE_KEY
cast send $L "borrow(uint256)"  1000000000000000000000         --rpc-url $RPC --private-key $PRIVATE_KEY

# read the health factor (should be 1.6e18 = 1.6)
cast call $L "healthFactor(address)(uint256)" <your address> --rpc-url $RPC

# oracle cuts the price: 2000 -> 1200
cast send $L "setPrice(uint256)" 1200000000000000000000 --rpc-url $RPC --private-key $PRIVATE_KEY

# read HF again (should be 0.96e18 = 0.96 < 1 -> liquidatable)
cast call $L "healthFactor(address)(uint256)" <your address> --rpc-url $RPC
```

> `<your address>` = anvil account 0 `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`.
> HF dropping from 1.6 to 0.96 is the exact moment right before "you get liquidated".
> When done: `pkill anvil`.

## Deploy to a testnet (Base Sepolia)

```bash
export PRIVATE_KEY=0xYourTestnetKey     # an account that holds some Base Sepolia gas
forge script script/DeployLend.s.sol --rpc-url base-sepolia --broadcast
```

The `base-sepolia` RPC alias is defined in `foundry.toml`.

## Dependencies

This project uses `forge-std`. If `lib/forge-std` is missing after cloning, run:

```bash
forge install foundry-rs/forge-std
```
