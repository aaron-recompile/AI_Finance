"""
Week 1 - Teacher faucet distributor: send a little test ETH to every student address
Reads student addresses from a list file (one per line), and sends AMOUNT_ETH to each from the
teacher/funder wallet (key in course/.env.faucet). Base Sepolia testnet only.

Setup once:
  - Fund the FUNDER address (see .env.faucet) from a faucet / your own wallet.
Run (from the course/ directory):
  set -a && source .env.faucet && set +a
  AMOUNT_ETH=0.001 ./ai_finance/bin/python weeks/week-01/code/faucet_distribute.py students.txt

install:  pip install web3
"""
import os
import sys
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com")   # reliable Base Sepolia RPC
AMOUNT = float(os.getenv("AMOUNT_ETH", "0.001"))
LIST = sys.argv[1] if len(sys.argv) > 1 else "students.txt"


def load_funder_key() -> str:
    """FUNDER_KEY from env, else walk up to find course/.env.faucet."""
    k = os.getenv("FUNDER_KEY")
    if k:
        return k
    for p in [Path.cwd(), *Path(__file__).resolve().parents]:
        f = p / ".env.faucet"
        if f.exists():
            for line in f.read_text().splitlines():
                if line.strip().startswith("FUNDER_KEY="):
                    return line.split("=", 1)[1].strip()
    raise SystemExit("FUNDER_KEY not found (set env, or create course/.env.faucet)")


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    acct = w3.eth.account.from_key(load_funder_key())

    addrs = [l.strip() for l in Path(LIST).read_text().splitlines()
             if l.strip() and not l.strip().startswith("#")]

    bal = w3.from_wei(w3.eth.get_balance(acct.address), "ether")
    print(f"Funder  {acct.address}   balance {bal} ETH   (chainId {w3.eth.chain_id})")
    print(f"Sending {AMOUNT} ETH to {len(addrs)} address(es) ...\n")

    nonce = w3.eth.get_transaction_count(acct.address)
    gp = w3.eth.gas_price
    for a in addrs:
        to = Web3.to_checksum_address(a)
        tx = {"from": acct.address, "to": to, "value": w3.to_wei(AMOUNT, "ether"),
              "nonce": nonce, "gas": 21000, "gasPrice": gp, "chainId": w3.eth.chain_id}
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        r = w3.eth.wait_for_transaction_receipt(h)
        ok = "OK  " if r.status == 1 else "FAIL"
        print(f"  {ok} {to}  +{AMOUNT} ETH  block {r.blockNumber}  tx 0x{h.hex().removeprefix('0x')[:12]}…")
        nonce += 1

    left = w3.from_wei(w3.eth.get_balance(acct.address), "ether")
    print(f"\nDone. Funder balance now {left} ETH")


if __name__ == "__main__":
    main()
