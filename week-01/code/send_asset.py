"""
Week 1 - Send an asset with code (R3): your first "write" transaction
Reading (read_chain.py) changes nothing; this one actually MOVES an asset and changes state.
Sign -> broadcast -> wait to be mined -> see the balances change: a transaction's full life.

Defaults to a local anvil chain (instant, free, pre-funded accounts); can point at testnet too:
    local:   anvil               # in another terminal
             python send_asset.py
    testnet: export RPC=https://sepolia.base.org
             export PRIVATE_KEY=0xYourTestnetKey      # needs faucet gas first
             export TO=0xRecipient
             python send_asset.py

install:  pip install web3
"""
import os
from web3 import Web3

RPC = os.getenv("RPC", "http://localhost:8545")
# Default = anvil account 0's well-known key (local chain, worthless). Use your own on testnet.
PRIVATE_KEY = os.getenv(
    "PRIVATE_KEY",
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
)
# Default recipient = anvil account 1
TO = Web3.to_checksum_address(
    os.getenv("TO", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
)
AMOUNT_ETH = float(os.getenv("AMOUNT_ETH", "1.0"))


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC} (run `anvil` first for local)"

    me = w3.eth.account.from_key(PRIVATE_KEY).address
    print(f"From   {me}")
    print(f"To     {TO}")
    print(f"Amount {AMOUNT_ETH} ETH\n")

    before_me = w3.eth.get_balance(me)
    before_to = w3.eth.get_balance(TO)
    print(f"Before: me {w3.from_wei(before_me,'ether')} ETH | them {w3.from_wei(before_to,'ether')} ETH")

    # 1) Assemble a transaction (a message that will change state)
    tx = {
        "from": me,
        "to": TO,
        "value": w3.to_wei(AMOUNT_ETH, "ether"),
        "nonce": w3.eth.get_transaction_count(me),   # counter that prevents replay
        "gas": 21000,                                 # plain transfer is a fixed 21000
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    }

    # 2) SIGN with the private key (proves it's you, without revealing the key)
    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)

    # 3) Broadcast -> get a transaction hash
    txh = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"\nBroadcast, tx hash = {txh.hex()}")

    # 4) Wait for it to be mined into a block
    rcpt = w3.eth.wait_for_transaction_receipt(txh)
    print(f"Mined in block #{rcpt.blockNumber}, status {'success' if rcpt.status==1 else 'failed'}")

    after_me = w3.eth.get_balance(me)
    after_to = w3.eth.get_balance(TO)
    print(f"\nAfter:  me {w3.from_wei(after_me,'ether')} ETH | them {w3.from_wei(after_to,'ether')} ETH")
    print(f"They +{w3.from_wei(after_to-before_to,'ether')} ETH; I -{w3.from_wei(before_me-after_me,'ether')} ETH (incl. gas)")

    print("\nTakeaways:")
    print("  - A transaction = assemble -> sign with the key -> broadcast -> mined; only then does value move.")
    print("  - You can now HOLD and TRANSFER an asset -- but 'transfer' is not 'trade':")
    print("    to swap ETH for USDC, nobody is waiting on the other side -> that's the AMM, Session 2.")


if __name__ == "__main__":
    main()
