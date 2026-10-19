# AI Finance — Bonus Homework 3

**Student:** Rongwen Weng
**GitHub Username:** rongwenweng-arch
**Course:** MB/CSE 599 — AI Finance

## Previous Homework

### `hw1/` — Week 1: environment setup and reading the chain
- `截图1.png` — Installing `web3` / `eth_account` in the `ai_finance` environment and checking the version.
- `截图2.png` — Running `gen_wallet.py` to create a learning wallet (public address only).
- `截图3.png` — Running `read_chain.py` to read ETH and USDC balances from Ethereum mainnet.

### `hw2/` — DeFi homework
- `DeFi_Homework_RONGWEN_WENG.pdf` — DeFi homework write-up with screenshots.

### `midterm/` — Mid-term, Track B: CrossFamilyRouter
- `Midterm_TrackB_RongwenWeng_v2.pdf` — Mid-term report.
- `strategy.py` — Strategy logic: `decide(view)` picks the best route across the four MAX/tUSDC venues (no RPC, no wallet).
- `my_strategy_bot.py` — On-chain adapter: scans all venues, buys on the chosen one, then re-routes the sell to whichever venue pays the most.

## Notes

All work was done for learning on test networks. No private keys, seed phrases or API keys are included.
