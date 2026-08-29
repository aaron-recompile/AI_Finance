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


def clean_addresses(raw_lines):
    """Parse messy student input: skip blanks/comments, validate, de-dupe (keep order)."""
    seen, good, bad = set(), [], []
    for line in raw_lines:
        s = line.strip().split()[0].strip() if line.strip() else ""   # tolerate trailing junk
        if not s or s.startswith("#"):
            continue
        try:
            a = Web3.to_checksum_address(s)          # validates format + checksum
        except Exception:
            bad.append(line.strip())
            continue
        if a in seen:
            continue                                 # de-dupe
        seen.add(a)
        good.append(a)
    return good, bad


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    chain_id = w3.eth.chain_id

    # SAFETY: this sends real value. Refuse to run on Ethereum mainnet by accident.
    if chain_id == 1:
        raise SystemExit("Refusing to run on Ethereum MAINNET (chainId 1). "
                         "This is a TESTNET faucet. Unset RPC or point it at a testnet.")

    acct = w3.eth.account.from_key(load_funder_key())
    addrs, bad = clean_addresses(Path(LIST).read_text().splitlines())
    if bad:
        print(f"⚠ Skipping {len(bad)} invalid line(s): " + ", ".join(b[:16] + "…" for b in bad) + "\n")
    if not addrs:
        raise SystemExit("No valid addresses to fund.")

    bal_wei = w3.eth.get_balance(acct.address)
    gp = w3.eth.gas_price
    amount_wei = w3.to_wei(AMOUNT, "ether")
    need_wei = (amount_wei + 21000 * gp) * len(addrs)      # rough total incl. gas
    print(f"Funder  {acct.address}")
    print(f"Balance {w3.from_wei(bal_wei,'ether')} ETH   (chainId {chain_id})")
    print(f"Plan    {AMOUNT} ETH x {len(addrs)} address(es)  ≈ need {w3.from_wei(need_wei,'ether')} ETH\n")
    if bal_wei < need_wei:
        raise SystemExit("Funder balance too low for this batch. Top it up, or lower AMOUNT_ETH.")

    nonce = w3.eth.get_transaction_count(acct.address)
    sent = 0
    for to in addrs:
        tx = {"from": acct.address, "to": to, "value": amount_wei,
              "nonce": nonce, "gas": 21000, "gasPrice": gp, "chainId": chain_id}
        try:
            h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
            r = w3.eth.wait_for_transaction_receipt(h)
            ok = "OK  " if r.status == 1 else "FAIL"
            print(f"  {ok} {to}  +{AMOUNT} ETH  block {r.blockNumber}  tx 0x{h.hex().removeprefix('0x')[:12]}…")
            nonce += 1                                # only advance on a successful broadcast
            if r.status == 1:
                sent += 1
        except Exception as e:
            # one bad address / transient RPC error shouldn't abort the whole class
            print(f"  ERR  {to}  {type(e).__name__}: {str(e)[:70]}  (skipped, will retry next run)")

    left = w3.from_wei(w3.eth.get_balance(acct.address), "ether")
    print(f"\nDone. Funded {sent}/{len(addrs)}. Funder balance now {left} ETH")


if __name__ == "__main__":
    main()
