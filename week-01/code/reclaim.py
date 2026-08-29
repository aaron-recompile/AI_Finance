"""
Week 1 - Reclaim (sweep) test ETH from group wallets back to the teacher/funder wallet
Reads a list of private keys (one per line) from a file; for each wallet, sends its
balance minus gas back to FUNDER_ADDRESS. Base Sepolia testnet only -> test coins don't
scatter; you recover them and reuse next class.

run (from course/):
  set -a && source .env.faucet && set +a   # provides FUNDER_ADDRESS
  ./ai_finance/bin/python weeks/week-01/code/reclaim.py group-keys.txt

install:  pip install web3
"""
import os
import sys
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com")
KEYS_FILE = sys.argv[1] if len(sys.argv) > 1 else "group-keys.txt"


def funder_address() -> str:
    a = os.getenv("FUNDER_ADDRESS")
    if a:
        return a
    for p in [Path.cwd(), *Path(__file__).resolve().parents]:
        f = p / ".env.faucet"
        if f.exists():
            for line in f.read_text().splitlines():
                if line.strip().startswith("FUNDER_ADDRESS="):
                    return line.split("=", 1)[1].strip()
    raise SystemExit("FUNDER_ADDRESS not found (set env, or course/.env.faucet)")


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    funder = Web3.to_checksum_address(funder_address())
    keys = [l.strip() for l in Path(KEYS_FILE).read_text().splitlines()
            if l.strip() and not l.strip().startswith("#")]

    gp = int(w3.eth.gas_price * 1.2)               # small bump to survive price fluctuation
    # Base is an OP-stack L2: besides L2 gas there is a separate L1 data fee. We can't predict it
    # exactly, so we leave a small BUFFER that comfortably covers L2 gas + L1 fee; the tiny leftover
    # (dust) stays in each wallet. Reclaims ~all of it without over-estimating.
    buffer = w3.to_wei(float(os.getenv("BUFFER_ETH", "0.00002")), "ether")
    print(f"Reclaiming to funder {funder}")
    print(f"Funder before: {w3.from_wei(w3.eth.get_balance(funder), 'ether')} ETH")
    print(f"gas {w3.from_wei(gp, 'gwei')} gwei; leave buffer {w3.from_wei(buffer, 'ether')} ETH/wallet; {len(keys)} wallet(s)\n")

    swept = 0
    for k in keys:
        acct = w3.eth.account.from_key(k)
        if acct.address.lower() == funder.lower():
            continue  # never sweep the funder into itself
        bal = w3.eth.get_balance(acct.address)
        if bal <= buffer:
            print(f"  skip {acct.address}  {w3.from_wei(bal, 'ether')} ETH (nothing to sweep)")
            continue
        value = bal - buffer                        # leave buffer for L2 gas + L1 fee
        tx = {"from": acct.address, "to": funder, "value": value,
              "nonce": w3.eth.get_transaction_count(acct.address),
              "gas": 21000, "gasPrice": gp, "chainId": w3.eth.chain_id}
        try:
            h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
            r = w3.eth.wait_for_transaction_receipt(h)
            ok = "OK  " if r.status == 1 else "FAIL"
            print(f"  {ok} {acct.address}  swept {w3.from_wei(value, 'ether')} ETH  tx 0x{h.hex().removeprefix('0x')[:12]}…")
            if r.status == 1:
                swept += value
        except Exception as e:
            print(f"  ERR  {acct.address}  {type(e).__name__}: {str(e)[:80]}")

    print(f"\nDone. Reclaimed {w3.from_wei(swept, 'ether')} ETH total.")
    print(f"Funder after:  {w3.from_wei(w3.eth.get_balance(funder), 'ether')} ETH")


if __name__ == "__main__":
    main()
