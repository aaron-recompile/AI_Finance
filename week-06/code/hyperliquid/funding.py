import requests

d = requests.post("https://api.hyperliquid.xyz/info", json={"type": "metaAndAssetCtxs"}).json()
meta, ctxs = d[0], d[1]

rows = []
for u, c in zip(meta["universe"], ctxs):
    f, mk, orc, prem = c.get("funding"), c.get("markPx"), c.get("oraclePx"), c.get("premium")
    if None in (f, mk, orc, prem):        # skip markets with missing fields (delisted/special)
        continue
    rows.append((u["name"], float(f), float(mk), float(orc), float(prem)))

def ann(f): return f * 24 * 365 * 100      # hourly rate -> annualized %

print(f"valid markets: {len(rows)}\n")
print(f"{'coin':6}{'ann funding':>12}{'mark':>12}{'oracle':>12}{'premium%':>11}")
for name in ["BTC", "ETH", "SOL"]:
    for n, f, mk, orc, prem in rows:
        if n == name:
            print(f"{n:6}{ann(f):>+11.1f}%{mk:>12.2f}{orc:>12.2f}{prem*100:>10.3f}%")

print("\nmost extreme funding right now (most lopsided / crowded) -- top 5:")
for n, f, mk, orc, prem in sorted(rows, key=lambda r: abs(r[1]), reverse=True)[:5]:
    side = "longs pay shorts (crowd long)" if f > 0 else "shorts pay longs (crowd short)"
    print(f"  {n:10} ann {ann(f):+9.1f}%  ->  {side}")
