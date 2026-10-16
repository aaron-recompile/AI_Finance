"""
Week 1 · Session 2 - INTERACT with a token you already issued: READ + TRANSFER.

Pairs with issue_asset.py. After you issue a token, this shows the TWO kinds of
contract call -- the core distinction used every week after:

  READ  (view)          token.functions.balanceOf(x).call()
                        -> ask only. free. changes nothing. no transaction.

  WRITE (state-change)  build_transaction -> sign -> send_raw_transaction -> wait
                        -> a real transaction. costs gas. moves the balance.

Flow:
    PRIVATE_KEY=0xYOURKEY TOKEN=0xTOKEN TO=0xRECIPIENT AMOUNT=250 python transfer_token.py

Defaults: RPC = Base Sepolia; TO = a demo address; AMOUNT = 250;
          PRIVATE_KEY = anvil account 0 (pass your own on a real chain).
For a local sandbox instead: RPC=http://localhost:8545 (with issue_asset.py + anvil).
install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com").strip()  # default: real testnet (viewable on an explorer)

# Pass your own key with PRIVATE_KEY=0x...  On a real chain you must.
# Falls back to the public anvil account 0 (worthless, local-only).
ANVIL_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
PRIVATE_KEY = os.getenv("PRIVATE_KEY", ANVIL_KEY).strip()
IS_LOCAL = ("localhost" in RPC) or ("127.0.0.1" in RPC)

TOKEN = os.getenv("TOKEN", "").strip()          # the token address printed by issue_asset.py
TO = os.getenv("TO", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8").strip()  # anvil account 1
AMOUNT = int(os.getenv("AMOUNT", "250").strip())

ABI = json.loads((Path(__file__).parent / "erc20_artifact.json").read_text())["abi"]


def read_balance(token, who, unit):
    """READ = a view call: .call() asks the node, returns a value, sends NO transaction."""
    raw = token.functions.balanceOf(who).call()      # <-- the read pattern
    return raw / unit


def transfer(w3, token, frm, pk, to, amount, unit):
    """WRITE = a state-changing call: assemble -> sign -> broadcast -> wait for the receipt."""
    tx = token.functions.transfer(to, amount * unit).build_transaction({   # <-- the write pattern
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
    assert TOKEN, "Set TOKEN=0x... (the token contract address you deployed)."
    if (not IS_LOCAL) and PRIVATE_KEY == ANVIL_KEY:
        raise SystemExit(
            "\nOn a real chain but no key given, so it fell back to the public anvil account,\n"
            "which holds none of your tokens -- transfer would fail. Pass your own key:\n"
            "   PRIVATE_KEY=0xYOURKEY TOKEN=... TO=... python transfer_token.py\n"
        )
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    me = w3.eth.account.from_key(PRIVATE_KEY).address
    to = Web3.to_checksum_address(TO)
    token = w3.eth.contract(address=Web3.to_checksum_address(TOKEN), abi=ABI)
    sym = token.functions.symbol().call()
    unit = 10 ** token.functions.decimals().call()   # scale by the token's own decimals (USDC=6, others may be 18)
    print(f"Me   {me}\nThem {to}\nToken {TOKEN} ({sym})\n")

    # (1) READ before
    print("(1) READ before (view -- free):")
    print(f"    me   = {read_balance(token, me, unit):,.0f} {sym}")
    print(f"    them = {read_balance(token, to, unit):,.0f} {sym}\n")

    # (2) WRITE: transfer
    print(f"(2) WRITE: transfer {AMOUNT} {sym} to them (sends a tx, costs gas) ...")
    rcpt = transfer(w3, token, me, PRIVATE_KEY, to, AMOUNT, unit)
    print(f"    mined in block #{rcpt.blockNumber}, status {'success' if rcpt.status == 1 else 'FAILED'}\n")

    # (3) READ after
    print("(3) READ after (view -- free):")
    print(f"    me   = {read_balance(token, me, unit):,.0f} {sym}")
    print(f"    them = {read_balance(token, to, unit):,.0f} {sym}")

    print("\nTakeaways:")
    print("  - READ  = .call()            -> ask only, free, no transaction (view).")
    print("  - WRITE = build/sign/send    -> a real tx, costs gas, changes the balance table.")
    print("  - 'transfer' moves the token, but it's a GIFT, not a trade -- no price, no counterparty.")
    print("    Trading with a price and no counterparty waiting = the AMM (next).")


if __name__ == "__main__":
    main()
