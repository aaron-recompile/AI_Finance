"""
Week 1 - Interact with a contract (R3): two kinds of contract call - read (view) and write
send_asset.py sent a NATIVE asset (ETH); this sends a TOKEN asset (ERC20).
A token transfer is not a plain transaction -- it's CALLING a contract's function. That's "interacting".

Three things:
  (1) deploy a ready-made token contract (just so we have something to talk to -- deploying is Week 2)
  (2) READ: call balanceOf (view) -- changes nothing, costs nothing
  (3) WRITE: call transfer (state-changing) -- changes state, sends a transaction

Defaults to a local anvil chain:
    anvil                     # in another terminal
    python interact_contract.py

install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "http://localhost:8545")
PRIVATE_KEY = os.getenv(
    "PRIVATE_KEY",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # anvil account 0
)
TO = Web3.to_checksum_address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")  # anvil account 1

ART = json.loads((Path(__file__).parent / "erc20_artifact.json").read_text())


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC} (run `anvil` first)"
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    me = acct.address
    print(f"Me   {me}\nThem {TO}\n")

    Token = w3.eth.contract(abi=ART["abi"], bytecode=ART["bytecode"])

    # (1) Deploy a token contract (to get an address we can interact with) -- details in Week 2
    tx = Token.constructor("Demo Token", "DEMO").build_transaction({
        "from": me, "nonce": w3.eth.get_transaction_count(me),
        "gas": 2_000_000, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id,
    })
    rcpt = w3.eth.wait_for_transaction_receipt(
        w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx, PRIVATE_KEY).raw_transaction))
    token_addr = rcpt.contractAddress
    token = w3.eth.contract(address=token_addr, abi=ART["abi"])
    print(f"(1) Deployed a token contract: {token.functions.symbol().call()} @ {token_addr}")

    # Mint 1000 to myself first (mint is also a write call)
    _send(w3, me, PRIVATE_KEY, token.functions.mint(me, 1000 * 10**18))

    # (2) READ: balanceOf is a view -- ask only, free
    print("\n(2) Read the contract (view, free):")
    print(f"    my balance   = {token.functions.balanceOf(me).call() / 10**18:,.0f} DEMO")
    print(f"    their balance= {token.functions.balanceOf(TO).call() / 10**18:,.0f} DEMO")

    # (3) WRITE: transfer changes state -- send a transaction moving 250 tokens
    print("\n(3) Write the contract (transfer, sends a tx): move 250 DEMO to them ...")
    r = _send(w3, me, PRIVATE_KEY, token.functions.transfer(TO, 250 * 10**18))
    print(f"    mined in block #{r.blockNumber}, status {'success' if r.status==1 else 'failed'}")

    print("\n    Read again (view):")
    print(f"    my balance   = {token.functions.balanceOf(me).call() / 10**18:,.0f} DEMO")
    print(f"    their balance= {token.functions.balanceOf(TO).call() / 10**18:,.0f} DEMO")

    print("\nTakeaways:")
    print("  - A token isn't the chain's native asset; it's just a balance table inside a contract.")
    print("  - Read (balanceOf) = view, ask-only, free; Write (transfer) = a tx, changes state, costs gas.")
    print("  - 'call vs send' / 'view vs state-changing' is used every week after (Week 2 AMM: read price / swap).")


def _send(w3, frm, pk, fn_call):
    """Assemble a contract-function call into a tx, sign, broadcast, wait for the receipt."""
    tx = fn_call.build_transaction({
        "from": frm, "nonce": w3.eth.get_transaction_count(frm),
        "gas": 200_000, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    return w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction))


if __name__ == "__main__":
    main()
