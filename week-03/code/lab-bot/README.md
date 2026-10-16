# Lab — Run Your Own On-Chain Bot (read-only)

Five bots that watch a shared testnet (Base Sepolia) and detect money-making
opportunities. **They only look — they never trade.** No wallet, no gas, no risk.

## One-time setup
You need Python 3. Then install one library:
```
python3 -m pip install web3
```

## Run it
```
./student_start.sh
```
Then open the dashboard in your browser:
```
http://localhost:8010/dashboard.html
```

## What to watch
Your five bots scan the chain every ~12 seconds. When the instructor **skews the
market**, a row lights up **GREEN** — your own program just spotted the opportunity,
independently, by reading the public chain. Different disturbances wake different bots:

| instructor does | bot that reacts |
|---|---|
| skews a DEX price | `dex-arb` / `swap-arb` (arbitrage) |
| cuts the oracle price | `liquidator` |
| spikes a lending rate | `rate-arb` |

## Stop
```
./student_start.sh stop
```

---
It's **DRY-RUN only**: it shows opportunities but never sends a transaction.
Want to see one actually fire? Watch the instructor's live dashboard on the projector —
and notice the opportunity vanish the instant a bot takes it.
