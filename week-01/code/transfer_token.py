"""
Week 1 · Session 2 - INTERACT with a token you already issued: READ + TRANSFER.

Pairs with issue_asset.py. After you issue a token, this shows the TWO kinds of
contract call -- the core distinction used every week after:

  READ  (view)          token.functions.balanceOf(x).call()
                        -> ask only. free. changes nothing. no transaction.

  WRITE (state-change)  build_transaction -> sign -> send_raw_transaction -> wait
                        -> a real transaction. costs gas. moves the balance.

Flow (keep the SAME anvil running as issue_asset.py, so the token still exists):
    anvil                                    # terminal A (leave running)
    python issue_asset.py                    # terminal B -> copy the "deployed at" address
    TOKEN=0xTHAT TO=0xRECIPIENT AMOUNT=250 python transfer_token.py

Defaults: TO = anvil account 1; AMOUNT = 250; PRIVATE_KEY = anvil account 0.
install:  pip install web3
"""
import json
import os
from pathlib import Path
from web3 import Web3

RPC = os.getenv("RPC", "https://base-sepolia-rpc.publicnode.com").strip()  # 默认真链,好在浏览器可视化

# --- 签名用的私钥:后台自动读,不写死在代码 ---
# 顺序:① 你显式传的 PRIVATE_KEY(学生用自己的)
#      ② 真链且没传时,自动读 course/.env.faucet 里的 FUNDER_KEY(老师演示,无需每次敲;该文件 gitignored)
#      ③ 都没有 → anvil 默认公开账户(本地沙盒)
ANVIL_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"  # anvil account 0 (public)


def _funder_key():
    """从 course 根目录 .env.faucet 读 FUNDER_KEY(gitignored,不进代码/仓库);没有则空字符串。"""
    env = Path(__file__).resolve().parents[3] / ".env.faucet"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("FUNDER_KEY") and "=" in line:
                return line.split("=", 1)[1].strip()
    return ""


_explicit = os.getenv("PRIVATE_KEY", "").strip()
_is_local = ("localhost" in RPC) or ("127.0.0.1" in RPC)
if _explicit:
    PRIVATE_KEY, KEY_SRC = _explicit, "PRIVATE_KEY (你传的)"
elif not _is_local and _funder_key():
    PRIVATE_KEY, KEY_SRC = _funder_key(), "funder (.env.faucet 后台自动读)"
else:
    PRIVATE_KEY, KEY_SRC = ANVIL_KEY, "anvil 默认账户 (本地)"

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
    if (not _is_local) and PRIVATE_KEY == ANVIL_KEY:
        raise SystemExit(
            "\n⚠️  你在真链(Base Sepolia)上,但没有可用的签名私钥,默认落回了 anvil 公开账户——\n"
            "   它在这条链上没有你的币,transfer 一定失败(就是刚才那个 status FAILED)。\n"
            "   解决:传自己的私钥再跑   PRIVATE_KEY=0x你的私钥 TOKEN=... TO=... python transfer_token.py\n"
            "   (老师机:确认 course/.env.faucet 里有 FUNDER_KEY,会自动用 funder,无需传 key。)\n"
        )
    w3 = Web3(Web3.HTTPProvider(RPC))
    assert w3.is_connected(), f"cannot connect to {RPC}"
    me = w3.eth.account.from_key(PRIVATE_KEY).address
    to = Web3.to_checksum_address(TO)
    token = w3.eth.contract(address=Web3.to_checksum_address(TOKEN), abi=ABI)
    sym = token.functions.symbol().call()
    unit = 10 ** token.functions.decimals().call()   # 问代币小数位;转 USDC(6)、转你自己的币(6/18)都自适应
    print(f"Me   {me}   [签名: {KEY_SRC}]\nThem {to}\nToken {TOKEN} ({sym})\n")

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
