#!/usr/bin/env python3
"""S6 arbitrage: OKX cash-and-carry (spot + perp) -- read-only, public endpoints only,
no key, no orders.

  How: buy spot + short the perp in equal size -> price moves cancel out (delta ~= 0)
  Earn: (1) perp funding rate (when positive, the short collects every 8h) (2) basis convergence at entry
  Pay:  fees on four fills (spot open/close + perp open/close), plus the risk the two legs don't fill together

Three sections:
  (1) now: spot price, perp price, basis, current funding rate
  (2) history: last 3 months of funding -> the real return of holding, and the share of negative periods
  (3) cost & plan: breakeven days + an "open plan" (JSON) -- this is the interface you later hand to Jarvis

Usage: python carry.py [NOTIONAL_USDT]     default 1000
Costs are assumptions (spot ~0.07% measured, perp taker ~0.05%, account rate not verified) -- edit the two constants below.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "okx"))
from okx_client import req

SPOT, SWAP = "BTC-USDT", "BTC-USDT-SWAP"
FEE_SPOT, FEE_SWAP = 0.0007, 0.0005          # one-side taker fee (assumed)
NOTIONAL = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0


def get(path):
    r = req("GET", path, private=False)
    if r.get("code") != "0":
        raise SystemExit(f"OKX error {r.get('code')} {r.get('msg')}")
    return r["data"]


# (1) now -- use book prices, not last: to actually fill, you buy spot at the ask, short perp at the bid
spot = get(f"/api/v5/market/ticker?instId={SPOT}")[0]
swap = get(f"/api/v5/market/ticker?instId={SWAP}")[0]
fr = get(f"/api/v5/public/funding-rate?instId={SWAP}")[0]
spot_ask, swap_bid = float(spot["askPx"]), float(swap["bidPx"])
basis = swap_bid / spot_ask - 1                # positive = perp dearer than spot = you lock in a gain at entry
rate = float(fr["fundingRate"])
next_t = datetime.fromtimestamp(int(fr["fundingTime"]) / 1000)
print("=== (1) now (fillable prices: buy spot at ask, short perp at bid) ===")
print(f"  spot ask {spot_ask:,.1f}   perp bid {swap_bid:,.1f}   basis {basis:+.3%}")
print(f"  current funding {rate:+.4%} / 8h  ~= annualized {rate * 3 * 365:+.1%}   next settle {next_t:%m-%d %H:%M}")
print(f"  (note: the two tickers are read one after another, not at the same instant -- the 'fake spread' from the execution layer)\n")

# (2) historical funding -- the public endpoint gives ~3 months, paginate through it
rows, after = [], ""
while True:
    d = get(f"/api/v5/public/funding-rate-history?instId={SWAP}&limit=100" + (f"&after={after}" if after else ""))
    if not d:
        break
    rows += d
    after = d[-1]["fundingTime"]
rates = [float(x["realizedRate"] or x["fundingRate"]) for x in rows]
days = len(rates) / 3
total = sum(rates)
neg = sum(r < 0 for r in rates)
first = datetime.fromtimestamp(int(rows[-1]["fundingTime"]) / 1000, timezone.utc)
print(f"=== (2) history: last {len(rates)} funding periods (since {first:%Y-%m-%d}, ~{days:.0f} days) ===")
print(f"  holding throughout (short perp) collected {total:+.3%}  -> annualized {total / days * 365:+.1%}")
print(f"  single period max {max(rates):+.4%}  min {min(rates):+.4%}   negative {neg}/{len(rates)} periods (the short pays in those)")
worst = min(sum(rates[i:i + 21]) for i in range(max(len(rates) - 20, 1)))
print(f"  worst 7-day stretch (21 periods) total {worst:+.3%}  -- carry is not free money, the rate turns on you\n")

# (3) cost, breakeven, plan
cost = 2 * FEE_SPOT + 2 * FEE_SWAP             # four fills
daily = total / days
be = cost / daily if daily > 0 else float("inf")
qty = round(NOTIONAL / spot_ask, 6)
print("=== (3) cost & breakeven ===")
print(f"  four fees: spot 2x{FEE_SPOT:.2%} + perp 2x{FEE_SWAP:.2%} = {cost:.2%}")
print(f"  at the last-3-months avg rate {daily:+.4%}/day -> breakeven ~{be:.1f} days"
      + ("" if be != float('inf') else " (avg rate <= 0: carry loses money over this window)"))
print(f"  entry basis {basis:+.3%} also counts: {'perp dearer, you gain at entry' if basis > 0 else 'perp cheaper, you lose at entry'} "
      f"{abs(basis):.3%} (realized only once it converges at close)")

plan = {
    "strategy": "cash_and_carry", "venue": "okx-demo", "notional_usdt": NOTIONAL,
    "legs": [
        {"instId": SPOT, "tdMode": "cash", "side": "buy", "ordType": "market", "sz": str(qty), "tgtCcy": "base_ccy"},
        {"instId": SWAP, "tdMode": "cross", "side": "sell", "ordType": "market",
         "sz": "contracts = qty / contract-value (ctVal); query /public/instruments before ordering"},
    ],
    "entry_check": {"basis_now": round(basis, 6), "funding_now": rate, "funding_avg_daily": round(daily, 6),
                    "breakeven_days": round(be, 1) if be != float("inf") else None},
    "exit_rules": ["funding negative 3 periods in a row", "basis converges below 0.02%", "held 30 days", "human says STOP"],
    "preconditions": ["account level acctLv >= 2 (spot-only mode can't trade perps)",
                      "only count the position open once BOTH legs are filled, otherwise immediately close the filled leg"],
}
print("\n=== open plan (print only, does not execute) -- when handed to Jarvis, this is what it outputs, waiting for you to say CONFIRM ===")
print(json.dumps(plan, ensure_ascii=False, indent=2))
