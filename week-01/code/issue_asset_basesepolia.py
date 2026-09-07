"""
Week 1 · Session 2 (ceremony) - ISSUE AN ASSET ON A REAL TESTNET: Base Sepolia.

Same idea as issue_asset.py, but instead of a throwaway local anvil chain, this puts
your token on the PUBLIC Base Sepolia testnet -- so it lives on-chain and anyone can
see it on a block explorer. Costs real testnet gas, so it uses the funded teacher wallet.

Difference from issue_asset.py:
  - defaults RPC to Base Sepolia (not localhost)
  - loads the funded teacher key from .env.faucet (FUNDER_KEY) automatically
  - after deploying, prints the BaseScan links so you can open it in class

Run (from anywhere; it finds .env.faucet at the course root):
    python issue_asset_basesepolia.py
Override:  NAME="Aaron Coin" SYMBOL=AARON SUPPLY=888888 python issue_asset_basesepolia.py

TESTNET ONLY -- never real money.  install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

HERE = Path(__file__).resolve()
COURSE_ROOT = HERE.parents[3]                      # code -> week-01 -> weeks -> course
ENV_FAUCET = COURSE_ROOT / ".env.faucet"

# --- load the funded teacher wallet from .env.faucet (FUNDER_KEY), unless PRIVATE_KEY is set ---
def load_env_file(p):
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out

_env = load_env_file(ENV_FAUCET)
RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com").strip()
PRIVATE_KEY = (os.getenv("PRIVATE_KEY") or _env.get("FUNDER_KEY", "")).strip()
NAME = os.getenv("NAME", "Aaron Coin").strip()
SYMBOL = os.getenv("SYMBOL", "AARON").strip()
SUPPLY = int(os.getenv("SUPPLY", "888888").strip())

ART = json.loads((HERE.parent / "erc20_artifact.json").read_text())
EXPLORER = "https://sepolia.basescan.org"


def send(w3, frm, pk, fn_call, gas):
    tx = fn_call.build_transaction({
        "from": frm, "nonce": w3.eth.get_transaction_count(frm),
        "gas": gas, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"      tx {h.hex()}  ... waiting for a real block ...")
    return w3.eth.wait_for_transaction_receipt(h)


def main():
    assert PRIVATE_KEY, f"No key. Put FUNDER_KEY in {ENV_FAUCET}, or pass PRIVATE_KEY=0x..."
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    chain = w3.eth.chain_id
    me = w3.eth.account.from_key(PRIVATE_KEY).address
    bal = w3.eth.get_balance(me) / 10**18

    print("=" * 60)
    print(f"  ISSUING '{NAME}' ({SYMBOL}) ON A REAL TESTNET")
    print("=" * 60)
    print(f"  network : Base Sepolia (chainId {chain})")
    print(f"  issuer  : {me}")
    print(f"  balance : {bal:.6f} ETH  (funded teacher wallet)")
    assert chain == 84532, f"Expected Base Sepolia (84532), got {chain}. Check RPC."
    assert bal > 0, "Issuer has 0 ETH on Base Sepolia -- can't pay gas. Fund it first."
    print()

    Token = w3.eth.contract(abi=ART["abi"], bytecode=ART["bytecode"])
    print(f"  (1) deploying the token contract ...")
    rcpt = send(w3, me, PRIVATE_KEY, Token.constructor(NAME, SYMBOL), gas=2_000_000)
    addr = rcpt.contractAddress
    token = w3.eth.contract(address=addr, abi=ART["abi"])
    print(f"      deployed at: {addr}  (block #{rcpt.blockNumber})\n")

    print(f"  (2) minting {SUPPLY:,} {SYMBOL} to the issuer ...")
    send(w3, me, PRIVATE_KEY, token.functions.mint(me, SUPPLY * 10**18), gas=200_000)
    print(f"      done.\n")

    print(f"  (3) read back (view, free):")
    print(f"      totalSupply = {token.functions.totalSupply().call() / 10**18:,.0f} {SYMBOL}")
    print(f"      my balance  = {token.functions.balanceOf(me).call() / 10**18:,.0f} {SYMBOL}\n")

    print("=" * 60)
    print("  IT'S LIVE. Open these in class:")
    print(f"  token   : {EXPLORER}/token/{addr}")
    print(f"  contract: {EXPLORER}/address/{addr}")
    print(f"  issuer  : {EXPLORER}/address/{me}")
    print("=" * 60)
    print("  (Explorer shows the token + transfers even though the contract")
    print("   is 'unverified' -- verifying source is a Week 2 step.)")


if __name__ == "__main__":
    main()
