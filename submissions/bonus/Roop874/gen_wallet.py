"""
Week 1 - Part 2: generate a wallet (a keypair), and see what to share vs. keep secret
A wallet is just a private key -> address. This makes one, so you can paste ONLY your address
in the chat. It also prints the private key, to drive the point home: you'd never paste that.

For learning only: treat any key printed here as disposable / testnet-only.
Never put real money behind a key you generated (or saw) in a classroom demo.

install:  pip install eth-account   (already in the ai_finance venv, via web3)
run:      python gen_wallet.py
"""
from eth_account import Account


def main():
    acct = Account.create()  # generate a fresh random keypair
    print("Your new wallet:\n")
    print(f"  ADDRESS      (public  - paste THIS in the chat) : {acct.address}")
    print(f"  PRIVATE KEY  (secret  - NEVER share, never paste): 0x{acct.key.hex().removeprefix('0x')}")
    print("\nNotice:")
    print("  - The address is derived from the private key by one-way math; you cannot go back.")
    print("  - Paste ONLY the address. You would never paste the private key even to look cool --")
    print("    because you already know, in your gut, what it protects.")
    print("  - This key is for learning only; never put real money behind a demo key.")


if __name__ == "__main__":
    main()
