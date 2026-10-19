"""strategy.py — HedgedPegBot (salman435-git): DeFi peg-keeper + Hyperliquid perp hedge.

ONE BOT, TWO VENUES
  Leg 1 (DeFi, Base Sepolia arena). The arena has two DEEP pools (CHEAP / DEAR, ~6M tUSDC each)
        and two SHALLOW pools (PoolA / PoolB, ~100-150k tUSDC each). Deep pools are expensive to
        move, so their liquidity-weighted price is our ORACLE for MAX's fair price. When a
        shallow pool trades more than BAND away from it, trade ONLY that pool (one leg) toward
        the oracle: below -> buy MAX with tUSDC, above -> sell MAX from inventory.
  Leg 2 (perp, Hyperliquid testnet). Leg 1 leaves us HOLDING MAX, so its gain is exposed to
        MAX's price. After each DeFi trade, re-size a SHORT ETH perpetual to the MAX inventory
        value, so a price drop on the inventory is offset by the short. MAX is the arena's ETH
        stand-in (it trades ~2000 like tETH), so ETH is the hedge proxy.

LEG 1 SIZING (closed form on x*y=k, fee ignored)
  Pool with reserves m (MAX), u (tUSDC), k = m*u. Price after the trade must be the target p*:
      buy  MAX: u' = sqrt(k * p*)  ->  dU = sqrt(k * p*) - u
      sell MAX: m' = sqrt(k / p*)  ->  dM = sqrt(k / p*) - m
  Trade STEP of that per heartbeat, capped by TRADE_CAP and the wallet.
  edge (marked to oracle): buy = MAX_received * oracle - tUSDC_paid ; sell = tUSDC_received - MAX_sold * oracle
  Fire only if edge >= MIN_EDGE (the 0.3% pool fee is inside the getAmountOut math).

LEG 2 SIZING
  target short = MAX inventory x oracle x USD_PER_TUSDC x HEDGE_RATIO, capped at HEDGE_CAP_USD.
  Arena tUSDC is free-mint play money, so it is scaled 1000:1 to fit a small testnet account.
  Rebalance only when off by more than REBAL_BAND_USD (Hyperliquid's $10 min order, no churn).

RULES
  1x cross leverage · 1% max slippage on both legs · drop the hedge if shorts would pay more than
  MAX_FUNDING_COST_H funding per hour · a file named STOP in this folder halts new trades ·
  `close` flattens the hedge.

KEYS (env vars only — never commit)
  AGENT_KEY     Base Sepolia wallet that trades the arena
  HL_AGENT_KEY  Hyperliquid trade-only API wallet (can trade, cannot withdraw)
  HL_MASTER     Hyperliquid main account the orders are booked under
  (or put HL_AGENT_KEY= / HL_MASTER= lines in a gitignored `.env.hl` next to this file)

    python run.py strategy                     # DRY-RUN both legs (no keys needed)
    python run.py strategy --live              # LIVE
    python strategy.py --fund 50000            # one-off: mint test tUSDC to AGENT_KEY's wallet
    python strategy.py status                  # both legs + net exposure
    python strategy.py close                   # flatten the Hyperliquid hedge
"""
import os, sys, time
from math import isqrt
from pathlib import Path
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from chain import w3, ADDR, at, erc20, send, ensure_allowance, acct_of

NAME = "hedged-peg"
WAD = 10 ** 18
HERE = Path(__file__).resolve().parent
STOP = HERE / "STOP"

# --- leg 1: DeFi peg-keeper ---
KEY = os.environ.get("AGENT_KEY")            # YOUR wallet — keep it out of git
ME = acct_of(KEY).address if KEY else None   # dry-run works without a key
SWAP_BPS = 30                  # 0.3% pool fee (same as the Router pools)
BAND = 0.02                    # act only if a shallow pool is >2% away from the oracle
STEP = 0.25                    # close 25% of the gap per heartbeat (don't overshoot others' trades)
TRADE_CAP = 10_000 * WAD       # max tUSDC (or tUSDC-worth of MAX) per trade
MIN_EDGE = 5 * WAD             # min expected profit, marked to oracle
SLIPPAGE = 0.01                # revert if we'd get >1% less than quoted (someone traded first)
SHALLOW = {"PoolA": "RouterA", "PoolB": "RouterB"}
DEEP = ("CHEAP", "DEAR")
_TOKEN0 = {}

# --- leg 2: Hyperliquid hedge ---
COIN, SZ_DEC = "ETH", 4            # Hyperliquid ETH perp, size precision 4 decimals
USD_PER_TUSDC = 0.001              # 1000 arena tUSDC of inventory -> $1 of hedge
HEDGE_RATIO = 1.0                  # 1.0 = fully hedged
HEDGE_CAP_USD = 200.0              # never short more than $200 notional
REBAL_BAND_USD = 11.0              # rebalance only if off by > $11 (min order is $10)
MAX_FUNDING_COST_H = 0.0005        # shorts paying > 0.05%/h -> drop the hedge


def _hl_env():
    env = {k: os.environ[k] for k in ("HL_AGENT_KEY", "HL_MASTER") if os.environ.get(k)}
    f = HERE / ".env.hl"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


_env = _hl_env()
MASTER = _env.get("HL_MASTER")
info = Info(constants.TESTNET_API_URL, skip_ws=True)
ex = (Exchange(Account.from_key(_env["HL_AGENT_KEY"]), constants.TESTNET_API_URL, account_address=MASTER)
      if _env.get("HL_AGENT_KEY") and MASTER else None)


# ===================== leg 1: DeFi =====================

def _shallow_reserves(pool):
    """(MAX reserve, tUSDC reserve) of a Uniswap-v2 style MAX/tUSDC pair."""
    p = at(ADDR[pool], "Pair")
    if pool not in _TOKEN0:
        _TOKEN0[pool] = p.functions.token0().call().lower()
    r0, r1 = p.functions.getReserves().call()
    return (r0, r1) if _TOKEN0[pool] == ADDR["MAX"].lower() else (r1, r0)


def _deep_reserves(pool):
    """(MAX reserve, tUSDC reserve) of a SimpleAMM pool (token0 = MAX)."""
    a = at(ADDR[pool], "SimpleAMM")
    return a.functions.reserve0().call(), a.functions.reserve1().call()


def _out(amount_in, r_in, r_out):
    a = amount_in * (10000 - SWAP_BPS)
    return a * r_out // (r_in * 10000 + a)


def oracle_price():
    """Liquidity-weighted MAX price of the deep pools, in tUSDC per MAX (float)."""
    m = u = 0
    for pool in DEEP:
        dm, du = _deep_reserves(pool)
        m, u = m + dm, u + du
    return u / m


def _plan(pool, oracle, usdc_bal, max_bal):
    """Decide side + size for one shallow pool. Returns a dict (size 0 = nothing to do)."""
    m, u = _shallow_reserves(pool)
    price = u / m
    dev = price / oracle - 1
    k = m * u
    target = int(oracle * WAD)                     # tUSDC per MAX, scaled by WAD
    if dev < 0:                                    # pool too cheap -> buy MAX with tUSDC
        side = "buy"
        full = isqrt(k * target // WAD) - u        # dU to reach the oracle price
        size = min(int(full * STEP), TRADE_CAP)
        if usdc_bal is not None:
            size = min(size, usdc_bal)
        got = _out(size, u, m) if size > 0 else 0  # MAX out
        edge = got * oracle - size if size > 0 else 0
    else:                                          # pool too dear -> sell MAX for tUSDC
        side = "sell"
        full = isqrt(k * WAD // target) - m        # dM to reach the oracle price
        size = min(int(full * STEP), int(TRADE_CAP / oracle))
        if max_bal is not None:
            size = min(size, max_bal)
        got = _out(size, m, u) if size > 0 else 0  # tUSDC out
        edge = got - size * oracle if size > 0 else 0
    return {"pool": pool, "price": price, "dev": dev, "side": side,
            "size": max(size, 0), "quote": got, "edge": edge}


def peg_scan():
    oracle = oracle_price()
    usdc_bal = erc20("tUSDC").functions.balanceOf(ME).call() if ME else None
    max_bal = erc20("MAX").functions.balanceOf(ME).call() if ME else None
    plans = [_plan(p, oracle, usdc_bal, max_bal) for p in SHALLOW]
    best = max(plans, key=lambda x: abs(x["dev"]))       # the most mispriced shallow pool
    hit = abs(best["dev"]) > BAND and best["size"] > 0 and best["edge"] >= MIN_EDGE
    unit = "tUSDC" if best["side"] == "buy" else "MAX"
    devs = " ".join(f"{x['pool'][-1]} {x['price']:.1f} ({x['dev']:+.1%})" for x in plans)
    line = (f"oracle {oracle:.1f} | {devs} | {best['side']} {best['size']/WAD:,.2f} {unit} "
            f"on {best['pool']} | edge {best['edge']/WAD:+,.2f}")
    if not ME:
        line += " | (no AGENT_KEY: sizing ignores wallet)"
    return {"hit": hit, "line": line, "oracle": oracle, **best}


def peg_fire(s):
    if not KEY:
        raise RuntimeError("set AGENT_KEY to trade")
    router = at(ADDR[SHALLOW[s["pool"]]], "Router")
    usdc, mx = erc20("tUSDC"), erc20("MAX")
    if s["side"] == "buy":
        tin, tout, held = "tUSDC", "MAX", mx
    else:
        tin, tout, held = "MAX", "tUSDC", usdc
    ensure_allowance(tin, ADDR[SHALLOW[s["pool"]]], key=KEY)
    min_out = int(s["quote"] * (1 - SLIPPAGE))
    before = held.functions.balanceOf(ME).call()
    rcpt = send(router.functions.swapExactTokensForTokens(
        s["size"], min_out, ADDR[tin], ADDR[tout], ME), key=KEY)
    # public RPC can lag a block behind the receipt; poll until the balance moves
    got = 0
    for _ in range(12):
        got = held.functions.balanceOf(ME).call() - before
        if got > 0:
            break
        time.sleep(0.5)
    if s["side"] == "buy":
        edge = got * s["oracle"] - s["size"]
    else:
        edge = got - s["size"] * s["oracle"]
    return {"tx": rcpt.transactionHash.hex(), "profit": round(edge / WAD, 2),
            "note": f"{s['side']} {s['size']/WAD:,.2f} {tin} on {s['pool']} -> {got/WAD:,.4f} {tout}"}


def fund(amount_usdc):
    """Mint test tUSDC to our wallet (the arena tokens are open-mint)."""
    if not KEY:
        raise RuntimeError("set AGENT_KEY first")
    mint_abi = [{"name": "mint", "type": "function", "stateMutability": "nonpayable",
                 "inputs": [{"type": "address"}, {"type": "uint256"}], "outputs": []}]
    t = w3.eth.contract(address=w3.to_checksum_address(ADDR["tUSDC"]), abi=mint_abi)
    rcpt = send(t.functions.mint(ME, int(amount_usdc * WAD)), gas=120_000, key=KEY)
    return rcpt.transactionHash.hex()


# ===================== leg 2: Hyperliquid hedge =====================

def perp_market():
    meta, ctx = info.meta_and_asset_ctxs()
    c = ctx[[a["name"] for a in meta["universe"]].index(COIN)]
    return {"mark": float(c["markPx"]), "funding": float(c["funding"])}


def perp_position():
    """Our ETH perp position on Hyperliquid (None if flat or no account configured)."""
    if not MASTER:
        return None
    for p in info.user_state(MASTER)["assetPositions"]:
        if p["position"]["coin"] == COIN:
            return p["position"]
    return None


def _inventory():
    """MAX held by the arena wallet (None in dry-run without AGENT_KEY)."""
    return erc20("MAX").functions.balanceOf(ME).call() if ME else None


def hedge_plan(oracle, inv_max, m, pos):
    """Target vs current short, both in ETH. short_now/target are positive numbers."""
    short_now = -float(pos["szi"]) if pos else 0.0
    inv_value = (inv_max or 0) / WAD * oracle                       # arena tUSDC
    target_usd = min(inv_value * USD_PER_TUSDC * HEDGE_RATIO, HEDGE_CAP_USD)
    reason = ""
    if m["funding"] < -MAX_FUNDING_COST_H:
        target_usd, reason = 0.0, "funding too costly for shorts"
    target = round(target_usd / m["mark"], SZ_DEC)
    drift_usd = (target - short_now) * m["mark"]
    return {"short_now": short_now, "target": target, "target_usd": target_usd,
            "drift_usd": drift_usd, "inv_value": inv_value, "reason": reason}


def rebalance_hedge(oracle):
    """Move the ETH short to the target for the CURRENT inventory. Returns a short result dict."""
    if ex is None:
        raise RuntimeError("set HL_AGENT_KEY and HL_MASTER to hedge")
    m, pos = perp_market(), perp_position()
    h = hedge_plan(oracle, _inventory(), m, pos)
    if abs(h["drift_usd"]) <= REBAL_BAND_USD:
        return {"action": "none", "short": h["short_now"]}
    diff = h["target"] - h["short_now"]            # > 0: short more (sell), < 0: buy back
    sz = round(abs(diff), SZ_DEC)
    if not pos:
        ex.update_leverage(1, COIN, is_cross=True)
    r = ex.market_open(COIN, diff < 0, sz, None, SLIPPAGE)
    st = r["response"]["data"]["statuses"][0]
    if "filled" not in st:
        raise RuntimeError(f"hedge order not filled: {st}")
    return {"action": "sell" if diff > 0 else "buy", "sz": sz, "px": float(st["filled"]["avgPx"]),
            "oid": st["filled"]["oid"], "short": round(h["target"], SZ_DEC)}


# ===================== the bot: scan() + fire() =====================

def scan():
    s = peg_scan()
    m, pos = perp_market(), perp_position()
    h = hedge_plan(s["oracle"], _inventory(), m, pos)
    hedge_hit = ex is not None and abs(h["drift_usd"]) > REBAL_BAND_USD   # no HL keys -> DeFi leg only
    stopped = STOP.exists()
    line = (f"{s['line']} || HL {COIN} {m['mark']:,.1f} fund {m['funding']*100:+.4f}%/h | "
            f"short {h['short_now']:.4f} -> {h['target']:.4f} ETH (${h['target_usd']:,.0f})")
    if h["reason"]:
        line += f" [{h['reason']}]"
    if stopped:
        line += " | STOP file: halted"
    return {**s, "peg_hit": s["hit"], "hedge_hit": hedge_hit, "hit": (s["hit"] or hedge_hit) and not stopped,
            "line": line}


def fire(s):
    out = {"tx": None, "profit": 0.0}
    if s["peg_hit"]:
        r = peg_fire(s)                             # leg 1: DeFi trade on Base Sepolia
        out.update(tx=r["tx"], profit=r["profit"], dex=r["note"])
    if ex is None:
        out["hedge"] = "skipped (HL_AGENT_KEY / HL_MASTER not set) — inventory is unhedged"
        return out
    h = rebalance_hedge(s["oracle"])                # leg 2: re-hedge the new inventory on Hyperliquid
    out["hedge"] = (f"{h['action']} {h['sz']} {COIN} @ {h['px']:,.1f} -> short {h['short']} (oid {h['oid']})"
                    if h["action"] != "none" else f"hedge ok, short {h['short']} {COIN}")
    return out


def status():
    oracle = oracle_price()
    inv = _inventory()
    m, pos = perp_market(), perp_position()
    h = hedge_plan(oracle, inv, m, pos)
    print(f"[{NAME}] DeFi leg : {inv/WAD if inv is not None else 0:,.4f} MAX x oracle {oracle:,.1f} = "
          f"{h['inv_value']:,.0f} tUSDC  (= ${h['inv_value']*USD_PER_TUSDC:,.2f} at hedge scale)")
    if pos:
        print(f"[{NAME}] perp leg : short {h['short_now']:.4f} {COIN} @ entry {float(pos['entryPx']):,.1f}, "
              f"mark {m['mark']:,.1f}, uPnL {float(pos['unrealizedPnl']):+.2f}, "
              f"funding since open {-float(pos['cumFunding']['sinceOpen']):+.2f} USDC")
    else:
        print(f"[{NAME}] perp leg : flat" + ("" if MASTER else " (HL_MASTER not set)"))
    net = h["inv_value"] * USD_PER_TUSDC - h["short_now"] * m["mark"]
    print(f"[{NAME}] net exposure ${net:+,.2f}  | target short {h['target']:.4f} {COIN}, "
          f"funding {m['funding']*100:+.4f}%/h" + (f" [{h['reason']}]" if h["reason"] else ""))


def close():
    """Flatten the Hyperliquid hedge (the MAX inventory stays in the arena wallet)."""
    if ex is None:
        raise RuntimeError("set HL_AGENT_KEY and HL_MASTER")
    if not perp_position():
        print(f"[{NAME}] no {COIN} position to close"); return
    r = ex.market_close(COIN, None, None, SLIPPAGE)
    print(f"[{NAME}] hedge closed:", r["response"]["data"]["statuses"][0])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "scan"
    if "--fund" in sys.argv:
        amt = float(sys.argv[sys.argv.index("--fund") + 1])
        print(f"[{NAME}] minted {amt:,.0f} tUSDC to {ME}: tx {fund(amt)}")
    elif cmd == "status":
        status()
    elif cmd == "close":
        close()
    else:
        s = scan()
        print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
        if s["hit"] and "--live" in sys.argv:
            print("  firing...", fire(s))
