# Build Your Own Flash-Loan Bot — Foundry Project (Week 3 flagship)

A real on-chain flash-loan arbitrage — self-contained, no external mainnet or RPC
needed. Everything (two DEXes, the lender, the bot) deploys together.

## Files

| File | What it is |
|------|------------|
| `src/FlashLender.sol` | The lender: lends → calls the borrower back → by the end of the callback, principal + fee **must** be repaid, otherwise the whole tx reverts |
| `src/Arbitrageur.sol` | Your bot: borrow USDC → buy ETH in the cheap pool → sell ETH in the dear pool → repay → keep the profit |
| `src/SimpleAMM.sol` / `src/MockERC20.sol` | The Week 2 AMM and test tokens, reused |
| `test/FlashLoan.t.sol` | (1) profitable arb (2) borrow too much → revert (3) lender unharmed after a revert |
| `script/DeployFlash.s.sol` | Deploy the whole demo: two DEXes with a price gap + a funded lender + the bot |
| `script/ResetGap.s.sol` | Re-open the 1950 / 2050 price gap after arbitrage has closed it (to re-run the class demo) |

## Run the tests (no network, no private key)

```bash
forge test -vv
```

Expected: **3 passed**. The profitable case prints a net profit of ~471 USDC — earned
from **zero starting capital**.

## The teaching points

- **Atomicity.** The final `require(repaid)` line in `FlashLender`, plus the EVM's
  all-or-nothing rule, is the *entire* guarantee behind "repaid within the same
  transaction". No collateral is needed because there is nothing to seize — if you
  don't repay, the chain rewinds everything.
- **Composability.** One call snaps four contract Legos together: borrow / buy / sell /
  repay.
- **Self-erasing arbitrage.** Borrow too much and your own trades flatten the price gap
  → you can't repay → the tx reverts (you lose only gas). That is `test_TooMuchReverts`.

## Deploy to a testnet (Base Sepolia)

```bash
export PRIVATE_KEY=0xYourTestnetKey     # an account that holds some Base Sepolia gas
forge script script/DeployFlash.s.sol --rpc-url base-sepolia --broadcast
```

The script prints the two DEX addresses, the `FlashLender`, and the `Arbitrageur`.
Trigger a real arbitrage from the `../../app/flashloan.html` one-click page, or from
`cast`:

```bash
cast send $ARB "run(uint256)" 20000000000000000000000 --rpc-url base-sepolia --private-key $PRIVATE_KEY
```

## Homework

Find the **optimal borrow amount** (profit peaks, then price impact eats it) and fold
the gas cost into your profit calculation. Prove your answer with a test.

## Dependencies

This project uses `forge-std`. If `lib/forge-std` is missing after cloning, run:

```bash
forge install foundry-rs/forge-std
```
