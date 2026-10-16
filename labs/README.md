# Labs — what we build, and how each piece works

These are the hands-on labs for the course. Most are interactive and run in your browser — open any of them and poke it. The exchange venues in part 2 run live in class.

Each piece is built from first principles, so the mechanism is visible instead of hidden behind a library.

---

## 1 · DeFi primitives (open in the browser)

### AMM / DEX — constant product `x·y=k`
How a pool sets a price with no order book, and why a bigger trade slips further along the curve. → **[open](https://aaron-recompile.github.io/AI_Finance/week-02/app/v2.html)**

![AMM / DEX](img/amm-dex.png)

### Lending & liquidation — the health factor
Supply collateral, borrow against it, and watch the health factor fall until a liquidation triggers. → **[open](https://aaron-recompile.github.io/AI_Finance/week-02/app/lend.html)**

![Lending](img/lending.png)

### Yield farming — emissions and real yield
Where the APY comes from, and why a reward token's price drifts down as everyone farms and sells. → **[open](https://aaron-recompile.github.io/AI_Finance/week-02/app/farm.html)**

![Yield farming](img/farming.png)

### Two-DEX arbitrage
The same asset at two prices: buying the cheaper pool and selling the dearer one moves them back together. → **[open](https://aaron-recompile.github.io/AI_Finance/week-03/app/arb.html)**

![Arbitrage](img/arbitrage.png)

### Flash-loan arbitrage — atomic
Borrow, arbitrage a deep pool against a shallow one, and repay in a single transaction — if the repayment fails, the whole transaction reverts. → **[open](https://aaron-recompile.github.io/AI_Finance/week-03/app/flashloan.html)**

![Flash loan](img/flashloan.png)

### Agent arena — bots on a live market
Five deterministic bots watch the pools and act the instant an opportunity appears; a dashboard tracks their P&L. Runs in the lab (`pip install web3`, then `./student_start.sh`, read-only).

![Agent arena](img/arena.png)

---

## 2 · Three venues on one matching engine

A single order-book matching engine underlies three venues. Each issues its own token and runs real deposit/withdraw on a testnet; students trade on them live in class.

![Architecture](architecture.svg)

**Spot** — instant matching on the book, with a background market maker to keep it liquid. → **[open the live demo](https://ai-finance.tail6afcc7.ts.net/)** *(runs on a class server; shared state, may be mid-reset)*

![Spot CEX](img/spot-cex.png)

**Perpetuals** — leverage and liquidation, with funding settled continuously to hold the mark near the index.

![Perpetuals](img/perp.png)

**Prediction market** — YES/NO shares whose price is the probability; an oracle resolves the event once.

![Prediction market](img/prediction.png)

---

## Notes

The DeFi pieces above are public — open and read them. The three exchange venues run live deposit/withdraw and hold wallet keys, so they're served to students as a running product rather than as source. The rest of the code is in [`week-02`](../week-02/)–[`week-07`](../week-07/).
