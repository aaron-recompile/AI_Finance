"""
Week 1 · Session 2 - INTERACT with a token you already issued: READ + TRANSFER.

Pairs with issue_asset.py. After you issue a token, this shows the TWO kinds of
contract call -- the core distinction used every week after:

  READ  (view)          token.functions.balanceOf(x).call()
                        -> ask only. free. changes nothing. no transaction.

  WRITE (state-change)  build_transaction -> sign -> send_raw_transaction -> wait
                        -> a real transaction. costs gas. moves the balance.

Flow (keep the SAME anvil running as issue_asset.py, so the token still exists):
    anvil                                    # terminal A (leave running)
    python issue_asset.py                    # terminal B -> copy the "deployed at" address
    TOKEN=0xTHAT TO=0xRECIPIENT AMOUNT=250 python transfer_token.py

Defaults: TO = anvil account 1; AMOUNT = 250; PRIVATE_KEY = anvil account 0.
install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "http://localhost:8545").strip()
PRIVATE_KEY = os.getenv(
    "PRIVATE_KEY",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # anvil account 0
).strip()
TOKEN = os.getenv("TOKEN", "").strip()          # the token address printed by issue_asset.py
TO = os.getenv("TO", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8").strip()  # anvil account 1
AMOUNT = int(os.getenv("AMOUNT", "250").strip())

ABI = json.loads((Path(__file__).parent / "erc20_artifact.json").read_text())["abi"]


def read_balance(token, who, sym):
    """READ = a view call: .call() asks the node, returns a value, sends NO transaction."""
    raw = token.functions.balanceOf(who).call()      # <-- the read pattern
    return raw / 10**18


def transfer(w3, token, frm, pk, to, amount):
    """WRITE = a state-changing call: assemble -> sign -> broadcast -> wait for the receipt."""
    tx = token.functions.transfer(to, amount * 10**18).build_transaction({   # <-- the write pattern
        "from": frm,
        "nonce": w3.eth.get_transaction_count(frm),
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)


def main():
    assert TOKEN, "Set TOKEN=0x... (the address issue_asset.py printed). Same anvil must still be running."
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC} (run `anvil` first)"
    me = w3.eth.account.from_key(PRIVATE_KEY).address
    to = Web3.to_checksum_address(TO)
    token = w3.eth.contract(address=Web3.to_checksum_address(TOKEN), abi=ABI)
    sym = token.functions.symbol().call()
    print(f"Me   {me}\nThem {to}\nToken {TOKEN} ({sym})\n")

    # (1) READ before
    print("(1) READ before (view -- free):")
    print(f"    me   = {read_balance(token, me, sym):,.0f} {sym}")
    print(f"    them = {read_balance(token, to, sym):,.0f} {sym}\n")

    # (2) WRITE: transfer
    print(f"(2) WRITE: transfer {AMOUNT} {sym} to them (sends a tx, costs gas) ...")
    rcpt = transfer(w3, token, me, PRIVATE_KEY, to, AMOUNT)
    print(f"    mined in block #{rcpt.blockNumber}, status {'success' if rcpt.status == 1 else 'FAILED'}\n")

    # (3) READ after
    print("(3) READ after (view -- free):")
    print(f"    me   = {read_balance(token, me, sym):,.0f} {sym}")
    print(f"    them = {read_balance(token, to, sym):,.0f} {sym}")

    print("\nTakeaways:")
    print("  - READ  = .call()            -> ask only, free, no transaction (view).")
    print("  - WRITE = build/sign/send    -> a real tx, costs gas, changes the balance table.")
    print("  - 'transfer' moves the token, but it's a GIFT, not a trade -- no price, no counterparty.")
    print("    Trading with a price and no counterparty waiting = the AMM (next).")


if __name__ == "__main__":
    main()
