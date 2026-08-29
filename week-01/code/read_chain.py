"""
Week 1 - Read the chain with code (R3): your first web3.py
Read-only, no private key, no gas. Reading the REAL chain is completely safe -- so we read
Ethereum MAINNET here. (Later, when we WRITE, we switch to a testnet -- writing is where risk lives.)

Network: Ethereum mainnet. Explorer: https://etherscan.io
  -> The block height and gas price here match what you see on etherscan.io right now.

install:  pip install web3
run:      python read_chain.py            # or set ADDR=0xYourAddress python read_chain.py
"""
import os
from web3 import Web3

# Public Ethereum mainnet RPC (read-only)
RPC = os.getenv("RPC", "https://ethereum-rpc.publicnode.com")
# USDC contract on Ethereum mainnet
USDC = Web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")

# Address to inspect. Default = vitalik.eth (holds both ETH and USDC). Override with ADDR=0x...
ADDR = Web3.to_checksum_address(
    os.getenv("ADDR", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
)

# Minimal ERC20 ABI: just the three read-only functions we need
ERC20_ABI = [
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "a", "type": "address"}], "outputs": [{"type": "uint256"}]},
    {"name": "decimals", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"type": "uint8"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"type": "string"}]},
]


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    print("Connected   :", w3.is_connected())
    print("Network     : Ethereum mainnet (chainId", str(w3.eth.chain_id) + ")")
    print("Latest block:", w3.eth.block_number, "  (compare on etherscan.io)")
    print("Gas price   :", round(float(w3.from_wei(w3.eth.gas_price, "gwei")), 3), "gwei")

    print(f"\nInspecting address: {ADDR}  (default: vitalik.eth)")

    # (1) Native balance (ETH): the node reads it straight from account state.
    #     This is Ethereum's ACCOUNT model: every address has a balance number.
    native = w3.eth.get_balance(ADDR)
    print(f"(1) Native ETH balance  (ask the node)     : {w3.from_wei(native, 'ether')} ETH")

    # (2) Token balance (USDC): USDC is just a contract; the balance lives inside
    #     the contract's own ledger, so we ASK THE CONTRACT (a view call).
    usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)
    sym = usdc.functions.symbol().call()
    dec = usdc.functions.decimals().call()
    bal = usdc.functions.balanceOf(ADDR).call()
    print(f"(2) Token {sym} balance (ask the contract) : {bal / 10**dec:,.2f} {sym}")
    print(f"    (contract {sym}, {dec} decimals, at {USDC})")

    print("\nTakeaways:")
    print("  - No node installed, nothing paid, no login: the chain is public, objective state.")
    print("  - Native vs token balance = two ledgers: one the node keeps, one inside the contract.")
    print("  - Reading is free and safe, so we read real mainnet. When we WRITE, we move to testnet.")
    print("  - Next (Week 2): you don't just read, you write -> send a tx, deploy a contract.")


if __name__ == "__main__":
    main()
