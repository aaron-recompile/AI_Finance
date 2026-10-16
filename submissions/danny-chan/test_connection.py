import os
from web3 import Web3

def test_rpc_connection():
    rpc_url = os.getenv("WEB3_PROVIDER_URI", "https://sepolia.base.org")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    print(f"Connected to Base Sepolia: {w3.is_connected()}")
    if w3.is_connected():
        print(f"Latest Block: {w3.eth.block_number}")

if __name__ == "__main__":
    test_rpc_connection()
