"""
Week 1 - Check a balance on ANY chain (the friendly "did my test ETH arrive?" tool)
Reads whatever chain your RPC points at (defaults to Base Sepolia testnet), shows the
native ETH balance for an address, and its USDC balance if we know USDC on that chain.
Never assumes mainnet, never crashes on a wrong chain -- just tells you what it sees.

Run:
  macOS / Linux:
    RPC=https://base-sepolia-rpc.publicnode.com ADDR=0xYourAddress python check_balance.py
  Windows (cmd / Anaconda Prompt) -- NO space after '=' :
    set RPC=https://base-sepolia-rpc.publicnode.com
    set ADDR=0xYourAddress
    python check_balance.py

install:  pip install web3
"""
import os
import sys
from web3 import Web3

# Default RPC = Base Sepolia (the testnet we fund students on). .strip() tolerates a
# stray space from Windows `set VAR= value`.
RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com").strip()

CHAIN_NAMES = {1: "Ethereum mainnet", 8453: "Base mainnet",
               84532: "Base Sepolia (testnet)", 11155111: "Ethereum Sepolia (testnet)"}

# USDC contract per chain (so we can show a token balance where we know it).
USDC_BY_CHAIN = {
    1:     "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    8453:  "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    84532: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
}

ERC20_ABI = [
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "a", "type": "address"}], "outputs": [{"type": "uint256"}]},
    {"name": "decimals", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"type": "uint8"}]},
    {"name": "symbol", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"type": "string"}]},
]


def get_address() -> str:
    """Address from ADDR env, else first CLI arg. Print friendly usage if missing/bad."""
    raw = (os.getenv("ADDR") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()
    if not raw:
        print("Which address? Set ADDR (or pass it as an argument).")
        print("  macOS/Linux : ADDR=0xYourAddress python check_balance.py")
        print("  Windows     : set ADDR=0xYourAddress   (no space after '=')  then  python check_balance.py")
        raise SystemExit(1)
    try:
        return Web3.to_checksum_address(raw)
    except Exception:
        raise SystemExit(f"'{raw}' is not a valid 0x... address (check for typos / stray spaces).")


def main():
    addr = get_address()
    w3 = Web3(Web3.HTTPProvider(RPC))
    if not w3.is_connected():
        raise SystemExit(f"Cannot connect to RPC: {RPC}")

    chain_id = w3.eth.chain_id
    name = CHAIN_NAMES.get(chain_id, "unknown network")
    print(f"Network : {name} (chainId {chain_id})")
    print(f"Address : {addr}\n")

    # Native ETH -- works on every chain
    native = w3.eth.get_balance(addr)
    print(f"ETH  (native)  : {w3.from_wei(native, 'ether')} ETH")

    # USDC -- only if we know the contract on this chain; never crash
    usdc_addr = USDC_BY_CHAIN.get(chain_id)
    if usdc_addr:
        try:
            c = w3.eth.contract(address=Web3.to_checksum_address(usdc_addr), abi=ERC20_ABI)
            dec = c.functions.decimals().call()
            sym = c.functions.symbol().call()
            bal = c.functions.balanceOf(addr).call()
            print(f"{sym} (token)   : {bal / 10**dec:,.2f} {sym}   (at {usdc_addr})")
        except Exception:
            print(f"USDC (token)   : could not read (RPC hiccup or no USDC at {usdc_addr}).")
    else:
        print("USDC (token)   : skipped (no known USDC address for this chain).")

    print("\nTip: verify the same numbers in a browser explorer for this chain "
          "(e.g. sepolia.basescan.org for Base Sepolia). The chain is public -- anyone can check.")


if __name__ == "__main__":
    main()
