"""
Week 1 · Session 2 (opener) - ISSUE AN ASSET with web3.py, then READ it.

The arc of the course in one script:
  1) ISSUE:  put a brand-new token on-chain (deploy a contract + mint supply to yourself)
  2) READ:   ask the token contract for a balance (view -- free, changes nothing)

That's it. Notice what's MISSING: you now own an asset, but there is NO WAY TO TRADE it --
nobody is on the other side. That gap is exactly what the AMM (next) fills.

Notes:
  - "Issue an asset" here = deploy a READY-MADE ERC-20 (erc20_artifact.json), just so we have
    a real token to hold and read. WRITING your own token contract is Week 2 (R4, MiniToken).
  - A token is NOT the chain's native coin (ETH). It's just a balance table living inside a
    contract. "Issuing" it = deploying that contract and minting the first balances.

Run on a local anvil chain (instant, free, no faucet):
    anvil                     # in another terminal, leave it running
    python issue_asset.py

Override (optional):  RPC=... PRIVATE_KEY=0x... NAME="My Coin" SYMBOL=MYC SUPPLY=1000000

install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "http://localhost:8545").strip()
PRIVATE_KEY = os.getenv(
    "PRIVATE_KEY",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",  # anvil account 0 (local, worthless)
).strip()
NAME = os.getenv("NAME", "Demo Token").strip()
SYMBOL = os.getenv("SYMBOL", "DEMO").strip()
SUPPLY = int(os.getenv("SUPPLY", "1000000").strip())  # human units; scaled by 18 decimals below

ART = json.loads((Path(__file__).parent / "erc20_artifact.json").read_text())


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC} (run `anvil` in another terminal first)"
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    me = acct.address
    print(f"Issuer (me): {me}\n")

    # ---- 1) ISSUE: deploy the token contract, then mint the whole supply to myself ----
    Token = w3.eth.contract(abi=ART["abi"], bytecode=ART["bytecode"])
    print(f"(1) Issuing asset '{NAME}' ({SYMBOL}) ...")

    # deploy = a state-changing tx: it puts new code (the token) at a fresh address
    deploy_rcpt = _send(w3, me, PRIVATE_KEY,
                        Token.constructor(NAME, SYMBOL), gas=2_000_000)
    token_addr = deploy_rcpt.contractAddress
    token = w3.eth.contract(address=token_addr, abi=ART["abi"])
    dec = token.functions.decimals().call()          # the token's decimals (this one = 6, like USDC)
    unit = 10 ** dec
    print(f"    deployed at: {token_addr}  (decimals={dec})")

    # mint = another state-changing tx: create SUPPLY tokens into my balance
    _send(w3, me, PRIVATE_KEY, token.functions.mint(me, SUPPLY * unit))
    print(f"    minted {SUPPLY:,} {SYMBOL} to myself\n")

    # ---- 2) READ: ask the contract for balances / supply (view = free, no tx) ----
    print("(2) Read the token (view -- ask only, costs nothing):")
    print(f"    name        = {token.functions.name().call()}")
    print(f"    symbol      = {token.functions.symbol().call()}")
    print(f"    totalSupply = {token.functions.totalSupply().call() / unit:,.0f} {SYMBOL}")
    print(f"    my balance  = {token.functions.balanceOf(me).call() / unit:,.0f} {SYMBOL}")

    print("\nTakeaways:")
    print(f"  - A token = a balance table inside a contract, NOT the chain's native ETH.")
    print(f"  - 'Issuing' it = deploy the contract (a tx) + mint balances (a tx).")
    print(f"  - READ (balanceOf/totalSupply) = view: free, changes nothing.")
    print(f"  - You now hold {SUPPLY:,} {SYMBOL} ... but there's NO ONE to trade with.")
    print(f"    A transfer just gives it away; there's no price, no counterparty.")
    print(f"    >>> That missing 'how do I swap it?' is exactly what the AMM answers next. <<<")


def _send(w3, frm, pk, fn_call, gas=200_000):
    """Assemble a contract call (or constructor) into a tx, sign, broadcast, wait for receipt."""
    tx = fn_call.build_transaction({
        "from": frm, "nonce": w3.eth.get_transaction_count(frm),
        "gas": gas, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    return w3.eth.wait_for_transaction_receipt(w3.eth.send_raw_transaction(signed.raw_transaction))


if __name__ == "__main__":
    main()
