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

# Public Ethereum mainnet RPC (read-only). .strip() tolerates a stray space from Windows `set`.
RPC = os.getenv("RPC", "https://ethereum-rpc.publicnode.com").strip()
# USDC contract on Ethereum mainnet
USDC = Web3.to_checksum_address("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")

# Address to inspect. Default = vitalik.eth (holds both ETH and USDC). Override with ADDR=0x...
# .strip() so `set ADDR= 0x..` (a common Windows typo with a leading space) still works.
ADDR = Web3.to_checksum_address(
    os.getenv("ADDR", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045").strip()
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


# Human names for the chain IDs you might land on in this course
CHAIN_NAMES = {1: "Ethereum mainnet", 8453: "Base mainnet",
               84532: "Base Sepolia (testnet)", 11155111: "Ethereum Sepolia (testnet)"}


def main():
    w3 = Web3(Web3.HTTPProvider(RPC))
    chain_id = w3.eth.chain_id
    name = CHAIN_NAMES.get(chain_id, "unknown network")
    print("Connected   :", w3.is_connected())
    print(f"Network     : {name} (chainId {chain_id})   RPC={RPC}")
    print("Latest block:", w3.eth.block_number, "  (compare on etherscan.io)")
    print("Gas price   :", round(float(w3.from_wei(w3.eth.gas_price, "gwei")), 3), "gwei")

    # This script is meant to read Ethereum MAINNET (chainId 1), where the USDC
    # address below lives. If we're somewhere else, it's almost always a leftover
    # RPC env var from a testnet exercise -- say so plainly instead of crashing.
    if chain_id != 1:
        print("\n" + "!" * 64)
        print(f"  You're on {name}, NOT Ethereum mainnet.")
        print("  This script reads mainnet USDC, which doesn't exist here.")
        print("  You most likely have an RPC env var set. Clear it and rerun:")
        print("     unset RPC          # macOS / Linux")
        print("     set RPC=           # Windows (Anaconda Prompt)")
        print("  ...then:  python read_chain.py")
        print("!" * 64)

    print(f"\nInspecting address: {ADDR}  (default: vitalik.eth)")

    # (1) Native balance (ETH): the node reads it straight from account state.
    #     This is Ethereum's ACCOUNT model: every address has a balance number.
    native = w3.eth.get_balance(ADDR)
    print(f"(1) Native ETH balance  (ask the node)     : {w3.from_wei(native, 'ether')} ETH")

    # (2) Token balance (USDC): USDC is just a contract; the balance lives inside
    #     the contract's own ledger, so we ASK THE CONTRACT (a view call).
    #     Wrapped so a wrong-chain / missing contract gives a clear hint, not a traceback.
    try:
        usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)
        sym = usdc.functions.symbol().call()
        dec = usdc.functions.decimals().call()
        bal = usdc.functions.balanceOf(ADDR).call()
        print(f"(2) Token {sym} balance (ask the contract) : {bal / 10**dec:,.2f} {sym}")
        print(f"    (contract {sym}, {dec} decimals, at {USDC})")
    except Exception:
        print("(2) Token USDC balance (ask the contract) : could not read.")
        print(f"    No USDC contract at {USDC} on this chain -> see the RPC note above.")

    print("\nTakeaways:")
    print("  - No node installed, nothing paid, no login: the chain is public, objective state.")
    print("  - Native vs token balance = two ledgers: one the node keeps, one inside the contract.")
    print("  - Reading is free and safe, so we read real mainnet. When we WRITE, we move to testnet.")
    print("  - Next (Week 2): you don't just read, you write -> send a tx, deploy a contract.")


if __name__ == "__main__":
    main()
