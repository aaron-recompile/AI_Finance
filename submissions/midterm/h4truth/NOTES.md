# Mid-term strategy notes

**Name:** Harry Wang
**GitHub:** h4truth
**Wallet:** 0xf2a5e7E2b614B410d2b0044A859D7147c2F2fcCF (Base Sepolia, funded by the instructor)

## Files
- `fair_value.py` — the strategy itself. `decide(view)` takes a snapshot of every
  MAX/tUSDC venue plus my balances and returns the one trade to make. No RPC, no wallet.
  `python fair_value.py` runs an offline self-check.
- `my_strategy_bot.py` — the arena adapter in the `scan()` + `fire()` shape. It reads the
  chain into the view, calls `decide()`, and sends the single transaction it returns.
  Copy both files into `week-03/code/lab-bot/` to run.

## What my strategy does
`consensus-maker` computes one **fair price** for MAX from all four venues at once — the
price the market would have if PoolA, PoolB, CHEAP and DEAR were poured into a single pool
(`sum of tUSDC reserves / sum of MAX reserves`, so deep pools count more than shallow ones).
It then looks for any single venue trading outside that consensus by more than the
round-trip fee. If a venue is **cheap**, the bot buys MAX there and holds it; if a venue
is **dear**, it sells MAX there from inventory. One transaction per fire, never two.

## Why it should make money
The arena is four separate pools for the same token, and they disagree — on the day I
built this, PoolA was ~7% below consensus and DEAR ~8% above. A pool that disagrees with
the depth-weighted consensus is the one that's mispriced, because moving a deep pool
takes real capital and moving a shallow one doesn't. Buying below consensus and selling
above it captures that disagreement minus 0.6% round-trip fees.

Every leg is scored as *edge versus fair* (`MAX received × fair − tUSDC paid` on a buy;
the mirror on a sell). Those two numbers add up to exactly the realized profit on a
completed buy-then-sell cycle, so the leaderboard figure is honest, just booked leg by
leg. Sizing is a grid search for the amount that maximizes edge after fees — it pushes
the venue only part way to fair, because the last few basis points cost more in price
impact than they return — capped at half my balance per fire.

The reason to do this in **one leg instead of two**: the provided arb bots (and the other
submission) buy on one venue and sell on another in two transactions, so the whole trade
is exposed to the price moving between the legs — a stranded leg is the documented failure
mode. Here each transaction is +EV on its own against the consensus and needs nothing to
happen afterward. The strategy is really market-making: it supplies the liquidity that
pulls outliers back to the market, and gets paid the spread for doing it.

## What would make it lose
- **The consensus can be wrong.** Fair is a weighted average of the same four pools, so if
  the instructor skews a *deep* pool, fair moves with it and the bot will happily buy
  "cheap" on a venue that is in fact correct. The mitigation is partial: the per-fire cap
  limits the damage and the next tick's re-read corrects the view, but a persistent skew
  of the deepest pool would drain inventory at bad prices.
- **Inventory risk.** After buying, I hold MAX until a venue is dear. If every venue drops
  together before that happens, the mark-to-fair edge I booked on the buy evaporates. The
  leg-edge accounting is only exact if fair is stable between the two legs.
- **Fees and slippage.** The threshold is 0.6% fees + 0.2% margin; a pool with a higher fee
  than the assumed 0.3% would make my estimates optimistic. Router legs carry a 1% min-out
  so they revert rather than lose; SimpleAMM legs have no min-out, so I re-read reserves
  right before sending and skip if the venue moved more than 1% since the scan.
- **Competition.** Two-leg arb bots take the biggest gaps first. When they do, my sell
  venue gets pulled down before I sell into it and I end up holding inventory longer.
- **Running out of one side.** With no MAX, the bot can only buy; with no tUSDC, only sell.
  It then waits for the matching opportunity rather than forcing a trade.

## Evidence
Run on 2026-10-19 from wallet `0xf2a5e7E2b614B410d2b0044A859D7147c2F2fcCF` via
`python orchestrator.py --only my_strategy_bot --live --interval 8` (Base Sepolia, chain id 84532).

- **First BUY leg** (12:01:20): bought 75.6266 MAX on PoolA for 45,500.20 tUSDC (avg 601.64 vs fair 1872.60)
  https://sepolia.basescan.org/tx/0xa0273ddc07c36dcfb4f51c18279574e5d039764a6b6afc1649185cbc74fc9fb5
- **First SELL leg** (12:02:46): sold 47.0460 MAX on DEAR for 92,207.49 tUSDC (avg 1959.94 vs fair 1924.38)
  https://sepolia.basescan.org/tx/0x2ad9ebf1f9a2cb4d4b057fc41cf580d4144afb678e476c778fa92a06398f5cd1
- Leaderboard: `consensus-maker` rank 1, 23 fires, booked leg edge +224,054.67 tUSDC
  (screenshot `dashboard_screenshot.png`, attached in the Classroom PDF).

All fires this session (one transaction each; edge is marked against the consensus price at scan time):

| # | time | side | venue | leg edge (tUSDC) | tx |
|---|---|---|---|---|---|
| 1 | 12:01:20 | BUY | PoolA | +95,693.14 | [0xa0273ddc…](https://sepolia.basescan.org/tx/0xa0273ddc07c36dcfb4f51c18279574e5d039764a6b6afc1649185cbc74fc9fb5) |
| 2 | 12:01:36 | BUY | PoolB | +33,401.33 | [0x3c68ea2d…](https://sepolia.basescan.org/tx/0x3c68ea2d9d62106bd9cce6654e635b35096ef004502fabd725299054b4af3a71) |
| 3 | 12:01:50 | BUY | PoolA | +14,647.74 | [0x146a34dc…](https://sepolia.basescan.org/tx/0x146a34dc58ccb1b4bec6091be723a002d76e81006e5787210f280dc79057246f) |
| 4 | 12:02:04 | BUY | PoolA | +6,302.66 | [0xd749c6d0…](https://sepolia.basescan.org/tx/0xd749c6d06ce57e9b5aa819787809d252058a4304d757be30896a481d5a8265c6) |
| 5 | 12:02:18 | BUY | PoolB | +3,127.55 | [0x7ea4732f…](https://sepolia.basescan.org/tx/0x7ea4732f5a53297d5bb96e87a00a0081a29135bad219a7dddffd38001e82896d) |
| 6 | 12:02:32 | BUY | PoolB | +1,487.74 | [0xbc837761…](https://sepolia.basescan.org/tx/0xbc837761c1b79b0472abd9d7c6f861703e7df7aa06fa7f7e983b30332db460e8) |
| 7 | 12:02:46 | SELL | DEAR | +1,401.34 | [0x2ad9ebf1…](https://sepolia.basescan.org/tx/0x2ad9ebf1f9a2cb4d4b057fc41cf580d4144afb678e476c778fa92a06398f5cd1) |
| 8 | 12:03:00 | BUY | PoolA | +30,763.99 | [0x2edb58d3…](https://sepolia.basescan.org/tx/0x2edb58d31184fa87c922a9ba47dbd0f25b432a96443768a9e35666c366e87f5f) |
| 9 | 12:03:14 | BUY | PoolB | +17,945.98 | [0xd2bdf656…](https://sepolia.basescan.org/tx/0xd2bdf65691acae21a673c91e86f5c4ae93dfeae5a9adce8bf1eae7931e38030d) |
| 10 | 12:03:28 | BUY | PoolB | +5,399.07 | [0xba332af7…](https://sepolia.basescan.org/tx/0xba332af7b47be39720885ff6bf455f017ba94a8dc1a8a02d380dfa07cf8d0cb1) |
| 11 | 12:03:42 | BUY | PoolA | +2,038.67 | [0xd158a92e…](https://sepolia.basescan.org/tx/0xd158a92ea74ccfd353211de93154ab7d41fd5abf0f167ff118825796cd1f6450) |
| 12 | 12:03:56 | BUY | PoolB | +1,052.32 | [0x7f9c3f13…](https://sepolia.basescan.org/tx/0x7f9c3f139e9070fd147cccbb291426373638ca2aefd016b80d08ce1a84c5a97d) |
| 13 | 12:04:12 | SELL | CHEAP | +552.57 | [0xaa79a203…](https://sepolia.basescan.org/tx/0xaa79a203bc9b581c18dd096ac585e76b877a3680cf76faf55fd74e9bd4cd05ab) |
| 14 | 12:04:26 | BUY | PoolA | +5,242.94 | [0x251845b0…](https://sepolia.basescan.org/tx/0x251845b0358e5b0d27fcb09d270b9d10b3095b8dd8809b60d438284dcd295a8c) |
| 15 | 12:04:40 | BUY | PoolB | +3,654.22 | [0x71534021…](https://sepolia.basescan.org/tx/0x71534021b6f10f3e897a858b48944c73d57ba6ec5a1ba908f6d2c4c3aafd5f6d) |
| 16 | 12:04:54 | BUY | PoolB | +904.26 | [0x6780b486…](https://sepolia.basescan.org/tx/0x6780b486b6c9e7cfbe1ed5858954cb238b4fab54e17f27253f9d196bc39c906d) |
| 17 | 12:05:08 | BUY | PoolB | +247.69 | [0x085ec632…](https://sepolia.basescan.org/tx/0x085ec632534c0774bb967858d25a6f4efdb44b320d784f2d6cf4c11353f76440) |
| 18 | 12:05:22 | BUY | PoolA | +107.01 | [0x4aaf95d4…](https://sepolia.basescan.org/tx/0x4aaf95d4e20d9548aa3104a1eef3e9fb519856165a3208ec2605dd5733824293) |
| 19 | 12:05:36 | BUY | PoolA | +44.30 | [0xe5377e4d…](https://sepolia.basescan.org/tx/0xe5377e4db4531611e852903ac855824123817679398a0fcb5affde3878e0a890) |
| 20 | 12:05:50 | BUY | PoolB | +22.17 | [0x22d7067e…](https://sepolia.basescan.org/tx/0x22d7067ee58bc1001d04eeef31ddfe3e016e6dd686d88ca19e97329862facd06) |
| 21 | 12:06:04 | BUY | PoolB | +10.34 | [0x34397b02…](https://sepolia.basescan.org/tx/0x34397b028c404ac795e2929cbe7f62c33dc3cd2bb930448e30b589e20e391615) |
| 22 | 12:06:18 | BUY | PoolA | +5.13 | [0xacbd9fae…](https://sepolia.basescan.org/tx/0xacbd9faeeb705564e9889733c469d5bf57068d6b38f3441dd99ea5307f0b8864) |
| 23 | 12:06:32 | BUY | PoolA | +2.53 | [0x5f4bf4e4…](https://sepolia.basescan.org/tx/0x5f4bf4e47dcdfaee784c276d256dcdd2ab706f976c06f8ef3333f708a4a30217) |

## Toward the Final (Track B → cross-venue)
`decide(view)` doesn't know what a venue is — it only needs `(base reserve, quote reserve)`
or, generalized, a price and a depth. Adding a fifth venue is one line in `VENUES`. For the
Final the plan is to feed it a Hyperliquid perp mark as a venue with the funding rate as a
carry term: when the perp trades above consensus and funding is positive, the "sell" leg
becomes a short perp that *collects* funding while the basis closes — the funding/basis
trade the brief describes, built on the same one-leg-versus-consensus logic.
