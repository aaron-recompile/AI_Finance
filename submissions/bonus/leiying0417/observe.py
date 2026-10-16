"""Keyless Base Sepolia observer. Never import or execute course bots."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import platform
import subprocess
import sys
import web3
from web3 import Web3, HTTPProvider

ROOT = Path(__file__).resolve().parent
COURSE = ROOT / "vendor/AI_Finance"
NAMES = ("tUSDC", "MAX", "RouterA", "RouterB", "PoolA", "PoolB")
RPCS = ("https://base-sepolia-rpc.publicnode.com", "https://sepolia.base.org")
ALLOWED = frozenset(("eth_chainId", "eth_blockNumber", "eth_getBlockByNumber", "eth_getCode", "eth_call"))

def fn(name, ins, outs, mut="view"):
    return {"type": "function", "name": name, "stateMutability": mut,
            "inputs": [{"name": "", "type": t} for t in ins],
            "outputs": [{"name": "", "type": t} for t in outs]}

PAIR_ABI = [fn("token0", [], ["address"]), fn("token1", [], ["address"]),
            fn("getReserves", [], ["uint112", "uint112"])]
TOKEN_ABI = [fn("decimals", [], ["uint8"])]
ROUTER_ABI = [fn("getAmountOut", ["uint256"] * 3, ["uint256"], "pure")]
# Exact view/pure selectors only; no swap/approve/mint even via eth_call.
SELECTORS = frozenset(Web3.keccak(text=s)[:4].hex() for s in (
    "token0()", "token1()", "getReserves()", "decimals()", "getAmountOut(uint256,uint256,uint256)"))

class ReadOnlyProvider(HTTPProvider):
    def __init__(self, uri):
        super().__init__(uri, request_kwargs={"timeout": 30, "headers": {
            "User-Agent": "Mozilla/5.0 (KeylessCourseObserver)", "Accept": "application/json"}})
        self.methods = Counter()
    def guard(self, method, params):
        if method not in ALLOWED:
            raise PermissionError(f"RPC method forbidden: {method}")
        if method == "eth_call":
            tx = params[0]
            if set(tx) - {"to", "data"}:
                raise PermissionError("Only keyless to/data calls allowed")
            data = tx.get("data", "")
            if data.removeprefix("0x")[:8] not in SELECTORS:
                raise PermissionError("Contract selector forbidden")
        self.methods[str(method)] += 1
    def make_request(self, method, params):
        self.guard(method, params)
        return super().make_request(method, params)
    def make_batch_request(self, requests):
        for method, params in requests:
            self.guard(method, params)
        return super().make_batch_request(requests)

def to_units(value, decimals):
    if isinstance(value, float):
        raise TypeError("Use decimal text, never float")
    with localcontext() as ctx:
        ctx.prec = 200
        n = Decimal(value) * (Decimal(10) ** decimals)
        if not n.is_finite() or n < 0 or n != n.to_integral_value():
            raise ValueError("Invalid amount or excess precision")
        return int(n)

def human(value, decimals):
    with localcontext() as ctx:
        ctx.prec = 200
        return format(Decimal(value) / (Decimal(10) ** decimals), "f")

def oriented(token0, token1, reserves, input_token, output_token):
    t0, t1, ti, to = (x.lower() for x in (token0, token1, input_token, output_token))
    if t0 == ti and t1 == to:
        return tuple(reserves)
    if t1 == ti and t0 == to:
        return tuple(reversed(reserves))
    raise ValueError("Pool tokens do not match requested pair")

def formula(amount, rin, rout):
    # Course dex_arb_bot.py: SWAP_BPS=30, _out(); compare, not assume deployed fee.
    a = amount * 9970
    return a * rout // (rin * 10000 + a)

def gross(output, principal):
    return output - principal

def load_addresses():
    # Parse literal public addresses only. No imports, eval, env access, or key files.
    tree = ast.parse((COURSE / "week-03/code/lab-bot/chain.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "ADDR" for t in n.targets))
    addresses = ast.literal_eval(node.value)
    overrides = json.loads((COURSE / "week-03/code/lab-bot/deployed.json").read_text())
    addresses.update(overrides)
    return {name: Web3.to_checksum_address(addresses[name]) for name in NAMES}

def git(*args):
    return subprocess.check_output(["git", "-C", str(COURSE), *args], text=True).strip()

def observe(report, rpc, block=None):
    provider = ReadOnlyProvider(rpc)
    w3 = Web3(provider)
    w3.middleware_onion.clear()  # no incidental account/gas RPC or signing middleware
    report.update(rpc=rpc, chain_id=w3.eth.chain_id)
    if report["chain_id"] != 84532:
        raise ValueError("Wrong chain")
    height = block if block is not None else w3.eth.block_number - 3
    header = w3.eth.get_block(height)
    report["block"] = {"number": height, "hash": Web3.to_hex(header["hash"]),
                       "timestamp": header["timestamp"],
                       "utc": datetime.fromtimestamp(header["timestamp"], timezone.utc).isoformat()}
    addresses = load_addresses()
    report["addresses"] = addresses
    report["code"] = {}
    for name, address in addresses.items():
        code = w3.eth.get_code(address, block_identifier=height)
        report["code"][name] = {"bytes": len(code), "keccak256": Web3.to_hex(Web3.keccak(code))}
        if not code:
            raise ValueError(f"No contract code: {name}")
    def contract(name, abi):
        return w3.eth.contract(address=addresses[name], abi=abi)
    def call(f):
        return f.call(block_identifier=height)
    decimals = {n: call(contract(n, TOKEN_ABI).functions.decimals()) for n in ("tUSDC", "MAX")}
    report["decimals"] = decimals
    report["pools"] = {}
    for name in ("PoolA", "PoolB"):
        p = contract(name, PAIR_ABI)
        t0, t1 = call(p.functions.token0()), call(p.functions.token1())
        rs = call(p.functions.getReserves())
        usd, mx = oriented(t0, t1, rs, addresses["tUSDC"], addresses["MAX"])
        report["pools"][name] = {"token0": t0, "token1": t1, "reserves_raw": list(map(str, rs)),
            "tUSDC_raw": str(usd), "MAX_raw": str(mx),
            "tUSDC": human(usd, decimals["tUSDC"]), "MAX": human(mx, decimals["MAX"])}
    report["router_quotes"] = []
    def quote(dex, amount, input_name, output_name):
        p = report["pools"]["Pool" + dex]
        rin, rout = oriented(p["token0"], p["token1"], list(map(int, p["reserves_raw"])),
                             addresses[input_name], addresses[output_name])
        result = call(contract("Router" + dex, ROUTER_ABI).functions.getAmountOut(amount, rin, rout))
        expected = formula(amount, rin, rout)
        report["router_quotes"].append({"router": "Router" + dex, "input_token": input_name,
            "output_token": output_name, "amount_in_raw": str(amount), "reserve_in_raw": str(rin),
            "reserve_out_raw": str(rout), "amount_out_raw": str(result),
            "course_30bps_formula_raw": str(expected), "matches_course_formula": result == expected})
        return result
    report["comparisons"] = []
    for principal in ("1", "10"):
        n = to_units(principal, decimals["tUSDC"])
        for first, second in (("A", "B"), ("B", "A")):
            mx = quote(first, n, "tUSDC", "MAX")
            output = quote(second, mx, "MAX", "tUSDC")
            diff = gross(output, n)
            report["comparisons"].append({"direction": first + "→" + second,
                "hypothetical_tUSDC": principal, "principal_raw": str(n), "MAX_out_raw": str(mx),
                "MAX_out": human(mx, decimals["MAX"]), "tUSDC_out_raw": str(output),
                "tUSDC_out": human(output, decimals["tUSDC"]), "gross_raw": str(diff),
                "gross_tUSDC": human(diff, decimals["tUSDC"])})
    end_header = w3.eth.get_block(height)
    report["block_hash_rechecked"] = Web3.to_hex(end_header["hash"])
    if header["hash"] != end_header["hash"]:
        raise RuntimeError("Reorg detected: discard snapshot")
    report["rpc_method_counts"] = dict(provider.methods)
    report["status"] = "ok"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", choices=RPCS, default=RPCS[0])
    parser.add_argument("--block", type=int)
    parser.add_argument("--output", default="reports/observation.json")
    args = parser.parse_args()
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "status": "incomplete",
        "python": platform.python_version(), "interpreter": sys.executable, "web3": web3.__version__,
        "course": {"source": git("remote", "get-url", "origin"), "commit": git("rev-parse", "HEAD"),
                   "git_status_porcelain": git("status", "--porcelain")},
        "notice": "观察用假设本金非交易授权。固定块静态组合报价，非有状态模拟、非可执行净利；未减未经验证的gas，不表示盈利。",
        "quote_semantics": "Router.getAmountOut(amountIn,reserveIn,reserveOut) is pure; reserves supplied from verified pool. This does not independently prove Router→Pool factory routing.",
        "abi_evidence": ["week-03/code/lab-bot/chain.py: Pair ABI, addresses, nonstandard 5-argument swap (no deadline)",
                         "week-02/app/v2.html:176,367 getAmountOut ABI and use", "week-03/code/lab-bot/dex_arb_bot.py: SWAP_BPS=30 and _out"],
        "limitations": ["No bytecode/source equivalence proof or router factory mapping verification", "Not atomic execution, no wallet balances/allowances/gas/profit validation"]}
    try:
        observe(report, args.rpc, args.block)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    path = (ROOT / args.output).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Report must remain inside project")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1

if __name__ == "__main__":
    raise SystemExit(main())
