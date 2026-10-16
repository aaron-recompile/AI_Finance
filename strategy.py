import os
import sys
import time
from web3 import Web3
from eth_account import Account

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
RPC_URL = os.getenv("BASE_SEPOLIA_RPC", "https://base-sepolia-rpc.publicnode.com")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY) if PRIVATE_KEY else None
MY_ADDRESS = account.address if account else "0x0"

POOL_A_ADDRESS = Web3.to_checksum_address(os.getenv("CHEAP_POOL", "0xc76a02903a3cf4ef62decaea3021771a41271eb4"))
POOL_B_ADDRESS = Web3.to_checksum_address(os.getenv("DEAR_POOL", "0x3d9f8ec22dc5fcc6b0e612d17e1df6bf5c879c8c"))
ARBITRAGEUR_ADDRESS = Web3.to_checksum_address(os.getenv("ARBITRAGEUR", "0xa642E2D17c5626be81d7628C53128118D22a2eF0"))

PAIR_ABI = [
    {"inputs": [], "name": "reserve0", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "reserve1", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
]

ARB_ABI = [
    {"inputs": [{"internalType": "uint256", "name": "borrowAmount", "type": "uint256"}], "name": "run", "outputs": [], "stateMutability": "nonpayable", "type": "function"}
]

pool_a = w3.eth.contract(address=POOL_A_ADDRESS, abi=PAIR_ABI)
pool_b = w3.eth.contract(address=POOL_B_ADDRESS, abi=PAIR_ABI)
arb_contract = w3.eth.contract(address=ARBITRAGEUR_ADDRESS, abi=ARB_ABI)

# ==========================================
# 2. CORE EVALUATION & EXECUTION
# ==========================================

def scan_and_evaluate(borrow_amount: int) -> dict:
    r0_a = pool_a.functions.reserve0().call()
    r1_a = pool_a.functions.reserve1().call()
    amount_bought = (r0_a * borrow_amount * 997) // (r1_a * 1000 + borrow_amount * 997)
    
    r0_b = pool_b.functions.reserve0().call()
    r1_b = pool_b.functions.reserve1().call()
    amount_returned = (r1_b * amount_bought * 997) // (r0_b * 1000 + amount_bought * 997)
    
    flash_fee = (borrow_amount * 5) // 10000
    net_profit = amount_returned - borrow_amount - flash_fee
    gap_pct = ((amount_returned - borrow_amount) / borrow_amount) * 100

    return {
        "net_profit": net_profit,
        "gap_pct": round(gap_pct, 4),
        "profitable": net_profit > 0
    }

def execute_flash_arb(borrow_amount: int):
    if not account or not PRIVATE_KEY:
        raise Exception("Private key missing.")
    
    # Fetch fresh nonce for each transaction in batch/single mode
    nonce = w3.eth.get_transaction_count(MY_ADDRESS)
    tx = arb_contract.functions.run(borrow_amount).build_transaction({
        'from': MY_ADDRESS,
        'gas': 300000,
        'maxFeePerGas': w3.to_wei('2', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('0.1', 'gwei'),
        'nonce': nonce,
    })
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"[+] Arbitrage transaction sent! Tx Hash: {w3.to_hex(tx_hash)}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise Exception("Arbitrage transaction reverted on-chain.")
    print(f"[+] Confirmed in block {receipt.blockNumber}")

# ==========================================
# 3. COMMAND CONTROLLER
# ==========================================

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "scan"
    borrow_size = 100 * 10**18  # 100 tUSDC default flash loan size
    
    print(f"[*] Agent Wallet: {MY_ADDRESS} | Command: {command}")

    if command == "scan":
        res = scan_and_evaluate(borrow_size)
        print(f"[*] Scan Result -> Gap: {res['gap_pct']}% | Net Profit: {res['net_profit'] / 10**18} tUSDC | Profitable: {res['profitable']}")

    elif command == "execute":
        res = scan_and_evaluate(borrow_size)
        print(f"[*] Pre-execution Check -> Gap: {res['gap_pct']}% | Net Profit: {res['net_profit'] / 10**18} tUSDC")
        if res['profitable']:
            print("[*] Executing single-shot arbitrage...")
            execute_flash_arb(borrow_size)
        else:
            print("[-] Not profitable. Aborting execution.")

    elif command == "batch":
        # Strictly read count from CLI argument provided by the agent orchestrator
        if len(sys.argv) > 2:
            try:
                count = int(sys.argv[2])
            except ValueError:
                print("[-] Error: Batch count must be a valid integer.")
                return
        else:
            print("[-] Error: Batch command requires a count argument (e.g., 'python3 strategy.py batch 5').")
            return

        if count <= 0 or count > 10:
            print("[-] Error: Batch limit must be between 1 and 10 shots for safety.")
            return
            
        print(f"[*] Starting bounded batch execution ({count} shots max)...")
        success_count = 0
        
        for i in range(1, count + 1):
            res = scan_and_evaluate(borrow_size)
            print(f"\n--- Shot {i}/{count} ---")
            print(f"[*] Gap: {res['gap_pct']}% | Net Profit: {res['net_profit'] / 10**18} tUSDC")
            
            if not res['profitable']:
                print("[-] Opportunity no longer profitable. Stopping batch early.")
                break
                
            try:
                execute_flash_arb(borrow_size)
                success_count += 1
                time.sleep(2)  # Brief buffer between transactions
            except Exception as e:
                print(f"[-] Execution failed on shot {i}: {e}")
                break
                
        print(f"\n[+] Batch completed. Successfully executed {success_count}/{count} shots.")
    else:
        print(f"[-] Unknown command: {command}. Use 'scan', 'execute', or 'batch <n>'.")