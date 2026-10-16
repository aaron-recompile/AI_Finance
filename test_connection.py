import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

rpc_url = os.getenv("RPC_URL", "https://sepolia.base.org")
private_key = os.getenv("PRIVATE_KEY")

print(f"Connecting to RPC: {rpc_url}...")
w3 = Web3(Web3.HTTPProvider(rpc_url))

# 1. Check connection status
if w3.is_connected():
    print("SUCCESS: Connected to Web3 provider!")
else:
    print("FAILURE: Could not connect to RPC URL. Check your network or RPC endpoint.")
    exit(1)

# 2. Check latest block number
try:
    block_number = w3.eth.block_number
    print(f"Latest Base Sepolia Block Number: {block_number}")
except Exception as e:
    print(f"Error fetching block number: {e}")

# 3. Check wallet balance if private key is provided
if private_key:
    try:
        account = w3.eth.account.from_key(private_key)
        balance_wei = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        print(f"Wallet Address: {account.address}")
        print(f"Wallet Balance: {balance_eth} ETH")
    except Exception as e:
        print(f"Error loading wallet from private key: {e}")
else:
    print("NOTICE: No PRIVATE_KEY found in environment variables (skipping balance check).")

print("Connection test complete!")
