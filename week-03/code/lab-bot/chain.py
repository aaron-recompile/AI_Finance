"""chain.py — the shared on-chain client every bot reuses.

One source of truth for: RPC, contract addresses, minimal ABIs, and the
build -> sign -> send transaction helper. Read helpers need no key; only
send() reads PRIVATE_KEY from the environment.
"""
import os
import time
from web3 import Web3

RPC = os.environ.get("RPC", "https://base-sepolia-rpc.publicnode.com")
CHAIN_ID = 84532  # Base Sepolia

# --- deployed contracts (Base Sepolia) ---
ADDR = {
    "tUSDC":       "0x6797beC4DC1D4444Fe81790c47e9FB91e491Ac69",
    "MAX":         "0x22201343039BB6418546978b447a45ee49f8dAa5",
    "FARM":        "0x026455e72a9dF06Fa4585F694d42E4cED13C01cd",

    # --- swap arb (flash) : two DEXes with a price gap + lender + bot ---
    "CHEAP":       "0xfE366315A4A21d34F875a737612e3Fe860bCd7f9",   # MAX @ 1950
    "DEAR":        "0x41c58Dc7eed3597FcDA9Cc6E42F11eB97b98CEff",   # MAX @ 2050
    "FlashLender": "0x1F765C16B1847579Ac90f095157E1A083BbBB51A",
    "Arbitrageur": "0x2Ba807B0CBB4290C4eEfd188909d621d3c957653",

    # --- real two-DEX (Uniswap-v2 style) : the pools students skew by hand ---
    "RouterA":     "0x2fc7C313bf38f0af4D92E8bE7347500D39174b82",
    "RouterB":     "0x19272Cae94B8e3BCd7d6752823F40b925C5dad3C",
    "PoolA":       "0xEf12cfd16d5e7903b837b2EfECBcdb1A0b5349D8",   # MAX/tUSDC on DEX-A
    "PoolB":       "0x07a45F3560d1bbF708027D9CcD8Ac95FBcaaD73d",   # MAX/tUSDC on DEX-B

    # --- farming ---
    "MasterChef":  "0xD13Dd4DE9dA5D1C862FEF8a08148e117507F7893",
    "FarmPool":    "0x8a7A067e065AB2C875E7AC21779f40004eeb9b2f",   # FARM/tUSDC (to sell FARM)

    # --- interest-rate arb + liquidation : Session-6 lending sandbox ---
    "LendA":       "0x9C9D02a09176801880c375c4797d9b4e45087f47",   # util ~0.30, low APR
    "LendB":       "0x88b6A22BFb2638208917DBB4A79216A3C977fc96",   # util ~0.80, high APR
}

# accounts we track (the borrower the LiquidatorBot watches)
BORROWER = "0x6c57b7a069061EA705C41ad6164ed27caf8324ec"  # funder/CSTU (position on LendB)

# setup_arena.py writes freshly-deployed addresses here (e.g. a new FARM/tUSDC pool);
# they override the defaults above without editing this file.
try:
    import json as __json
    __dep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deployed.json")
    if os.path.exists(__dep):
        ADDR.update(__json.load(open(__dep)))
except Exception:
    pass

def _fn(name, ins, outs, mut="view"):
    return {"name": name, "type": "function", "stateMutability": mut,
            "inputs": [{"type": t} for t in ins], "outputs": [{"type": t} for t in outs]}

ABI = {
    "SimpleAMM": [_fn("reserve0", [], ["uint256"]), _fn("reserve1", [], ["uint256"]),
                  _fn("token0", [], ["address"]), _fn("token1", [], ["address"]),
                  _fn("getAmountOut", ["uint256", "uint256", "uint256"], ["uint256"], "pure"),
                  _fn("swap0For1", ["uint256"], ["uint256"], "nonpayable"),
                  _fn("swap1For0", ["uint256"], ["uint256"], "nonpayable"),
                  _fn("addLiquidity", ["uint256", "uint256"], ["uint256"], "nonpayable")],
    "Arbitrageur": [_fn("run", ["uint256"], [], "nonpayable"), _fn("owner", [], ["address"])],
    "ERC20": [_fn("balanceOf", ["address"], ["uint256"]),
              _fn("approve", ["address", "uint256"], ["bool"], "nonpayable"),
              _fn("allowance", ["address", "address"], ["uint256"])],
    "Pair": [_fn("getReserves", [], ["uint112", "uint112"]),
             _fn("token0", [], ["address"]), _fn("token1", [], ["address"])],
    "Router": [_fn("swapExactTokensForTokens",
                   ["uint256", "uint256", "address", "address", "address"], ["uint256"], "nonpayable")],
    "MasterChef": [_fn("pendingFarm", ["uint256", "address"], ["uint256"]),
                   _fn("deposit", ["uint256", "uint256"], [], "nonpayable"),
                   _fn("userInfo", ["uint256", "address"], ["uint256", "uint256"])],
    "LendingPool": [_fn("supplyAPR", [], ["uint256"]), _fn("utilization", [], ["uint256"]),
                    _fn("healthFactor", ["address"], ["uint256"]),
                    _fn("currentDebt", ["address"], ["uint256"]),
                    _fn("collateralOf", ["address"], ["uint256"]),
                    _fn("price", [], ["uint256"]), _fn("shares", ["address"], ["uint256"]),
                    _fn("setPrice", ["uint256"], [], "nonpayable"),
                    _fn("liquidate", ["address", "uint256"], [], "nonpayable"),
                    _fn("supply", ["uint256"], [], "nonpayable"),
                    _fn("withdraw", ["uint256"], [], "nonpayable"),
                    _fn("postCollateral", ["uint256"], [], "nonpayable"),
                    _fn("borrow", ["uint256"], [], "nonpayable"),
                    _fn("cash", [], ["uint256"])],
}

w3 = Web3(Web3.HTTPProvider(RPC))


ENV_FAUCET = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.faucet")


def _key():
    """Signing key: PRIVATE_KEY env if set, else FUNDER_KEY from .env.faucet."""
    k = os.environ.get("PRIVATE_KEY")
    if k:
        return k
    try:
        for line in open(ENV_FAUCET):
            line = line.strip()
            if line.startswith("FUNDER_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    raise RuntimeError("no PRIVATE_KEY in env and FUNDER_KEY not found in .env.faucet")


def acct():
    """The funder signing account (default signer for setup / disturb)."""
    return w3.eth.account.from_key(_key())


def acct_of(key):
    """Account for a specific private key — each bot has its own wallet."""
    return w3.eth.account.from_key(key)


import json as _json  # noqa: E402
BOT_KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bots.keys.json")


def load_bot_key(name):
    """A bot's own private key from bots.keys.json (written by setup_arena.py).
    Fallback: if the file/key is absent (e.g. the student DRY-RUN bundle, which ships
    no keys), return a throwaway key so imports still work. It never signs a real fire
    in dry-run; if someone did go --live with it, the unfunded wallet just reverts."""
    try:
        with open(BOT_KEYS_FILE) as f:
            return _json.load(f)[name]
    except (FileNotFoundError, KeyError):
        return w3.eth.account.create().key.hex()


def contract(name, abi_key=None):
    return w3.eth.contract(address=Web3.to_checksum_address(ADDR[name]), abi=ABI[abi_key or name])


def at(addr, abi_key):
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ABI[abi_key])


def erc20(name_or_addr):
    a = ADDR.get(name_or_addr, name_or_addr)
    return w3.eth.contract(address=Web3.to_checksum_address(a), abi=ABI["ERC20"])


def send(fn, gas=800_000, retries=5, key=None, gas_price=None):
    """build -> sign -> send -> wait. `key` picks the signer (a bot's own wallet);
    default is the funder. Retries on nonce races and raises on on-chain revert.
    `gas_price` (wei) lets you BID higher to win the ordering race — within a block,
    higher priority lands first. Default = the node's suggested price (everyone ties)."""
    a = acct_of(key) if key else acct()
    last = None
    for i in range(retries):
        try:
            tx = fn.build_transaction({
                "from": a.address,
                "nonce": w3.eth.get_transaction_count(a.address, "pending"),
                "gas": gas,
                "gasPrice": int(gas_price) if gas_price else w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })
            signed = a.sign_transaction(tx)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            rcpt = w3.eth.wait_for_transaction_receipt(h)
            if rcpt.status != 1:
                raise RuntimeError(f"tx reverted on-chain: {h.hex()}")
            return rcpt
        except Exception as e:
            m = str(e).lower()
            if any(k in m for k in ("nonce", "already known", "replacement transaction underpriced")):
                last = e
                time.sleep(0.7 + 0.5 * i)
                continue
            raise
    raise last


def ensure_allowance(token, spender_addr, min_amount=2 ** 255, key=None):
    """Approve `spender` to pull `token` from the signer (funder, or a bot's wallet)."""
    t = erc20(token)
    me = (acct_of(key) if key else acct()).address
    spender = Web3.to_checksum_address(ADDR.get(spender_addr, spender_addr))
    if t.functions.allowance(me, spender).call() < min_amount:
        send(t.functions.approve(spender, 2 ** 256 - 1), gas=120_000, key=key)
