"""fair_value.py — ConsensusMaker: the decision logic (Track B mid-term).

No RPC, no wallet, no transactions in this file. `decide(view)` takes a snapshot
of every MAX/tUSDC venue plus my balances and answers "what single trade, if any,
should I make right now?". my_strategy_bot.py is the thin on-chain adapter.

IDEA — one-leg market making against a cross-venue consensus price
  The arena quotes MAX/tUSDC on four venues (PoolA, PoolB, CHEAP, DEAR). Every
  venue is a constant-product pool, so if you imagine pouring all four into ONE
  pool, its price would be   fair = sum(tUSDC reserves) / sum(MAX reserves).
  That is the depth-weighted consensus: a deep pool pulls it hard, a small
  skewed pool barely moves it.

  The provided bots (and the other submission) do TWO-leg arbitrage: buy here,
  sell there, in two transactions, and eat the risk that the price moves between
  the legs — a stranded leg is the documented failure mode.

  This bot does ONE leg at a time. If a venue is cheaper than fair by more than
  the round-trip fee, BUY MAX there and hold it. If a venue is dearer than fair
  by more than the fee, SELL MAX there from inventory. Each leg is +EV on its
  own, marked against the consensus. Over a cycle the two legs add up to exactly
  the realized round-trip profit — but no single transaction is ever exposed to
  the other venue moving.

  Sizing: push the venue's price only part-way back to fair (grid search for the
  size that maximizes edge after fees), capped by balance and a per-fire cap.

VIEW
    {"venues": {name: (MAX reserve, tUSDC reserve), ...},   # wei
     "usdc": my tUSDC balance (wei),  "max": my MAX balance (wei)}

Run `python fair_value.py` for an offline self-check with synthetic reserves.
"""

NAME = "consensus-maker"

WAD = 10 ** 18
FEE_BPS = 30                      # 0.3% per swap on every venue
RT_BPS = 2 * FEE_BPS              # a leg only counts if the other leg is also paid for
MARGIN_BPS = 20                   # extra cushion above fees before we act
MIN_PROFIT = 1 * WAD              # 1 tUSDC — same floor as the reference bots
MAX_FRACTION = 0.5                # never commit more than half a balance in one fire
GRID = 200


def quote(amount_in, r_in, r_out, fee_bps=FEE_BPS):
    """Constant-product output with fee — same formula the pools use."""
    a = amount_in * (10000 - fee_bps)
    return a * r_out // (r_in * 10000 + a)


def fair_price(venues):
    """Depth-weighted consensus: merge every pool into one and read its price."""
    um = sum(u for _, u in venues.values())
    mm = sum(m for m, _ in venues.values())
    return um / mm if mm else 0.0


def deviation(venue, fair):
    m, u = venue
    return (u / m) / fair - 1.0


def _best_buy(venue, fair, usdc):
    """Spend D tUSDC on `venue`; value the MAX received at fair minus the exit fee."""
    m, u = venue
    cap = int(usdc * MAX_FRACTION)
    if cap <= 0:
        return 0, 0
    best_p, best_d = -(1 << 255), 0
    step = max(1, cap // GRID)
    for i in range(1, GRID + 1):
        d = i * step
        out = quote(d, u, m)
        p = int(out * fair * (10000 - FEE_BPS) / 10000) - d
        if p > best_p:
            best_p, best_d = p, d
    return best_p, best_d


def _best_sell(venue, fair, maxbal):
    """Sell q MAX on `venue`; compare tUSDC received with q valued at fair."""
    m, u = venue
    cap = int(maxbal * MAX_FRACTION)
    if cap <= 0:
        return 0, 0
    best_p, best_q = -(1 << 255), 0
    step = max(1, cap // GRID)
    for i in range(1, GRID + 1):
        q = i * step
        out = quote(q, m, u)
        p = out - int(q * fair * (10000 + FEE_BPS) / 10000)
        if p > best_p:
            best_p, best_q = p, q
    return best_p, best_q


def decide(view):
    venues, usdc, maxbal = view["venues"], view["usdc"], view["max"]
    fair = fair_price(venues)
    threshold = (RT_BPS + MARGIN_BPS) / 10000
    devs = {n: deviation(v, fair) for n, v in venues.items()}

    candidates = []
    for n, v in venues.items():
        d = devs[n]
        if d < -threshold:
            p, size = _best_buy(v, fair, usdc)
            if size:
                candidates.append(("BUY", n, size, p))
        elif d > threshold:
            p, size = _best_sell(v, fair, maxbal)
            if size:
                candidates.append(("SELL", n, size, p))

    line_px = " ".join(f"{n}:{(v[1]/v[0]):.0f}({devs[n]*100:+.1f}%)" for n, v in venues.items())
    if not candidates:
        outside = [n for n, d in devs.items() if abs(d) > threshold]
        if outside:   # mispriced venues exist, but we hold nothing on the side needed to act
            need = sorted({"tUSDC" if devs[n] < 0 else "MAX" for n in outside})
            why = (f"{','.join(outside)} outside ±{threshold*100:.2f}% "
                   f"but no {'/'.join(need)} balance to act")
        else:
            why = f"no venue outside ±{threshold*100:.2f}%"
        return {"hit": False, "fair": fair, "devs": devs, "line": f"fair {fair:.1f} | {line_px} | {why}"}

    side, venue, size, profit = max(candidates, key=lambda c: c[3])
    unit = "tUSDC" if side == "BUY" else "MAX"
    return {"hit": profit >= MIN_PROFIT, "side": side, "venue": venue, "size": size,
            "profit": profit / WAD, "fair": fair, "devs": devs,
            "line": f"fair {fair:.1f} | {line_px} | {side} {size/WAD:,.4g} {unit} on {venue} "
                    f"est {profit/WAD:+,.2f}"}


# ------------------------------------------------------------------ self-check
if __name__ == "__main__":
    # Roughly the arena as observed in the other submission: PoolA ~1750, DEAR ~2023.
    venues = {
        "PoolA": (100 * WAD, 175_000 * WAD),
        "PoolB": (100 * WAD, 190_000 * WAD),
        "CHEAP": (50 * WAD, 97_500 * WAD),
        "DEAR":  (50 * WAD, 101_150 * WAD),
    }
    fair = fair_price(venues)
    print(f"fair = {fair:.2f}")
    for n, v in venues.items():
        print(f"  {n:6s} price {v[1]/v[0]:8.2f}  dev {deviation(v, fair)*100:+.2f}%")

    print("\nStep 1 — funded with 5,000 tUSDC, no MAX:")
    s1 = decide({"venues": venues, "usdc": 5_000 * WAD, "max": 0})
    print("  ", s1["line"], "->", "HIT" if s1["hit"] else "skip")
    assert s1["hit"] and s1["side"] == "BUY" and s1["venue"] == "PoolA"

    # simulate the fill
    m, u = venues["PoolA"]
    got = quote(s1["size"], u, m)
    venues["PoolA"] = (m - got, u + s1["size"])
    print(f"   filled: paid {s1['size']/WAD:,.2f} tUSDC for {got/WAD:.4f} MAX "
          f"(avg {s1['size']/got:.2f}, fair {fair:.2f})")

    print("\nStep 2 — now holding MAX:")
    s2 = decide({"venues": venues, "usdc": 5_000 * WAD - s1["size"], "max": got})
    print("  ", s2["line"], "->", "HIT" if s2["hit"] else "skip")
    assert s2["hit"] and s2["side"] == "SELL" and s2["venue"] == "DEAR"
    m, u = venues["DEAR"]
    usd_back = quote(s2["size"], m, u)
    print(f"   filled: sold {s2['size']/WAD:.4f} MAX for {usd_back/WAD:,.2f} tUSDC")

    # Mark-to-fair profits of the two legs vs realized cash on the MAX that cycled
    realized = usd_back - s2["size"] * s1["size"] // got
    print(f"\nLeg edges: buy {s1['profit']:+.2f}, sell {s2['profit']:+.2f} "
          f"| realized on the cycled MAX: {realized/WAD:+.2f} tUSDC")

    print("\nFlat market check (all venues within fees):")
    flat = {n: (100 * WAD, int(1900.0 * 100 * WAD * (1 + k))) for n, k in
            zip(venues, (0.000, 0.002, -0.002, 0.001))}
    s3 = decide({"venues": flat, "usdc": 5_000 * WAD, "max": 1 * WAD})
    print("  ", s3["line"], "->", "HIT" if s3["hit"] else "skip")
    assert not s3["hit"]
    print("\nself-check OK")
