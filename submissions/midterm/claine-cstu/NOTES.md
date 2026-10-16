# Mid-term Strategy Notes — NexusRouter

**Name:** Andrew Claine
**GitHub:** claine-cstu
**Wallet:** `0xf8Fd0BC5Fbe6Aaa77318F4a836936af02B706D1e`

---

## Strategy Overview & Files
- [`strategy.py`](strategy.py) — **Pure Mathematical & Decision Logic**: Free of any network/web3 dependencies. Analyzes a market `view` snapshot, evaluates all $N \times (N-1)$ directed venue pairs using analytical closed-form convex optimization, verifies edge hurdles, and detects stranded inventory for automated self-unwinding.
- [`my_strategy_bot.py`](my_strategy_bot.py) — **On-Chain Adapter**: Queries live Base Sepolia reserves across all four MAX/tUSDC venues, interfaces with `run.py` and `orchestrator.py` via `scan()` and `fire()`, executes Leg 1 with slippage floors, performs live Leg 2 adaptive re-routing, and manages ERC-20 allowances.

---

## What My Strategy Does
`NexusRouter` is an autonomous cross-family liquidity router and statistical arbitrage engine. The arena contains four constant-product pools quoting `MAX/tUSDC`:
1. Two SimpleAMM pools (`CHEAP` @ ~1,983 tUSDC, `DEAR` @ ~1,996 tUSDC) with deep ~$6M reserves.
2. Two Uniswap-v2 pools (`PoolA` @ ~437 tUSDC, `PoolB` @ ~477 tUSDC) with volatile ~$115k–$140k reserves.

While the course's default bots are restricted to intra-family trading (`arb_bot` only trades CHEAP↔DEAR; `dex_arb_bot` only trades PoolA↔PoolB), `NexusRouter` unifies all four venues into a single unified order routing graph. Every tick, it dynamically sweeps all directed pool pairs, computes the exact closed-form optimal trade size $D^*$ constrained by wallet capital, executes Leg 1 on the cheapest pool with slippage protection, and adaptively re-routes Leg 2 to whichever pool offers the highest real-time exit price. It also features an automated **Safety Shield** that detects stranded inventory and unwinds it at the best venue.

---

## Why It Should Make Money
1. **Structural Market Disconnect**: The two AMM families are architecturally separated—Uniswap-v2 requires router contract calls and pair tokens, whereas SimpleAMM is a standalone custom contract. Because default bots do not bridge the two protocols, massive pricing divergences persist (currently PoolA is priced at ~437 tUSDC/MAX while DEAR is priced at ~1,996 tUSDC/MAX, representing a >350% gross spread against only 0.6% in total round-trip swap fees).
2. **Analytical Closed-Form Sizing**: For constant product pools with fee factor $\gamma = 0.997$, chaining two swaps produces an output equation:
   $$u_{out}(D) = \frac{a \cdot D}{b + c \cdot D}$$
   where $a = \gamma^2 m_1 u_2$, $b = m_2 u_1$, and $c = m_2 + \gamma m_1$.
   Rather than resorting to imprecise heuristics or discrete grid searches, `NexusRouter` computes the exact derivative $\frac{dP}{dD} = 0$, yielding the global maximum at:
   $$D^* = \frac{\sqrt{a \cdot b} - b}{c}$$
   By trading $\min(D^*, \text{balance})$, the bot maximizes total profit per heartbeat while preventing excessive slippage.
3. **Adaptive Real-Time Re-Routing**: In two-leg arbitrage, market prices can shift between transaction confirmations. By re-sampling all venues immediately after Leg 1 lands, the bot routes Leg 2 to whichever venue provides the highest marginal recovery.

---

## What Would Make It Lose
1. **Execution Latency & Legged Risk (Non-Atomic Execution)**: Unlike flash loan transactions that revert atomically upon failure, executing across two distinct protocols requires two separate on-chain transactions. If a competing bot or pool skew lands between Leg 1 and Leg 2, the exit price could deteriorate. `NexusRouter` mitigates this with a strict 1% slippage floor on router legs and the Leg 2 real-time re-route.
2. **Edge Decay & Competitive Crowding**: As `NexusRouter` trades, each buy pushes the cheap pool's price up, and each sell pushes the dear pool's price down. Once the price spread compresses within the 0.60% round-trip fee threshold plus the 20 bps hurdle rate, the edge closes and the bot halts until new dislocations appear.
3. **Gas Volatility on L2**: If Base Sepolia base fee or priority gas spikes drastically, transaction gas overhead could eat into the net profit of smaller trade sizes.

---

## Evidence & Verification
- **Offline Mathematical Self-Check:**
  ```text
  === nexus-router Offline Self-Check ===
  Decision with 1,000 tUSDC capital:
  Action: trade | Hit: True
  [CHEAP: 2000.0 | DEAR: 2000.0 | PoolA: 439.4 | PoolB: 479.2] => ARBITRAGE: Buy PoolA (439.4) -> Sell CHEAP (2000.0) | spread +355.2% | size 1,000.0 tUSDC | est profit +3,490.19 tUSDC (349.02%)
  [OK] Sizing and directional routing passed.
  [OK] Stranded inventory unwind logic passed.
  All self-check tests passed successfully!
  ```

- **Live Base Sepolia Chain Scan (Block #48167897+):**
  ```text
  [nexus-router] [CHEAP: 1983.2 | DEAR: 1996.1 | PoolA: 437.7 | PoolB: 477.5] => ARBITRAGE: Buy PoolA (437.7) -> Sell DEAR (1996.1) | spread +356.1% | size 1,000.0 tUSDC | est profit +3,498.62 tUSDC (349.86%) -> HIT
  ```

- **Simulated / Mock Execution against Live Base Sepolia Reserves:**
  ```text
  === Executing Mock Trade against Live Base Sepolia Reserves ===
    action: trade (mock/simulated)
    tx: 0xmock6ad15ee5f78999bce6e0f7e1ad905c310b34153e
    buy_venue: PoolA
    sell_venue: DEAR
    size_spent_tUSDC: 1000.0
    max_traded: 2.2621
    usdc_returned: 4498.62
    profit: +3498.62 tUSDC (+349.86% ROI)
    note: Simulated execution against live Base Sepolia reserves: Buy PoolA -> Sell DEAR
  ```

- **Live On-Chain Transaction Hashes:**
  *(When funded with Base Sepolia gas ETH, paste live tx hash from `python my_strategy_bot.py --live`)*:
  - Tx Hash: `https://sepolia.basescan.org/tx/0x...`

