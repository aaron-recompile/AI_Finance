"""
Week 1 - R5 preview: wrap chain operations as "tools an agent can call" (framework-agnostic)
In class you did three things by hand: read balance / send asset / interact with a contract.
This wraps them as clean tool functions + a guardrail, so any agent framework (OpenClaw, ...) can plug in.
Core idea: the agent only REQUESTS a tool call; before it executes it must pass the Guard
(caps + whitelist) -- this is the seed of the Week 5 signer.

run demo:  python agent_tools.py       (needs anvil first)
homework:  wire these tools into your own agent (OpenClaw), see openclaw-agent.template.jsonc

install:  pip install web3
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from web3 import Web3

ART = json.loads((Path(__file__).parent / "erc20_artifact.json").read_text())


# ---------------------------- Guard (seed of the Week 5 signer) ----------------------------
@dataclass
class Guard:
    """Hard rules the agent must pass before moving money/assets. The AI cannot change it."""
    eth_cap: float                       # per-call ETH transfer cap
    token_cap: float                     # per-call token transfer cap
    whitelist: set[str]                  # only these recipients are allowed
    log: list = field(default_factory=list)

    def check(self, to: str, amount: float, cap: float, unit: str) -> tuple[bool, str]:
        if Web3.to_checksum_address(to) not in self.whitelist:
            return False, f"blocked: {to[:10]} not on whitelist"
        if amount > cap:
            return False, f"blocked: {amount:g} over per-call cap {cap:g} {unit}"
        return True, "allowed"


# ---------------------------- Tools (callable by an agent) ----------------------------
class ChainTools:
    """Expose chain operations as methods an agent can call. Every WRITE passes the Guard first."""

    def __init__(self, rpc: str, private_key: str, guard: Guard, token_addr: str | None = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        assert self.w3.is_connected(), f"cannot connect to {rpc}"
        self.acct = self.w3.eth.account.from_key(private_key)
        self.guard = guard
        self.token = self.w3.eth.contract(address=token_addr, abi=ART["abi"]) if token_addr else None

    # -- read-only: no state change, no guard needed --
    def get_eth_balance(self, address: str) -> dict:
        """Get an address's native ETH balance."""
        wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
        return {"ok": True, "address": address, "eth": float(self.w3.from_wei(wei, "ether"))}

    def get_token_balance(self, address: str) -> dict:
        """Get an address's token balance (requires token set)."""
        raw = self.token.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return {"ok": True, "address": address, "token": raw / 10**18}

    # -- write: changes state, must pass the Guard --
    def send_eth(self, to: str, amount_eth: float) -> dict:
        """Send native ETH to an address (passes the guard)."""
        ok, why = self.guard.check(to, amount_eth, self.guard.eth_cap, "ETH")
        if not ok:
            return {"ok": False, "blocked_by_guard": why}
        r = self._sign_send({**self._base(), "to": Web3.to_checksum_address(to),
                             "value": self.w3.to_wei(amount_eth, "ether"), "gas": 21000})
        self.guard.log.append(("send_eth", to, amount_eth))
        return {"ok": True, "tx": r.transactionHash.hex(), "block": r.blockNumber}

    def transfer_token(self, to: str, amount: float) -> dict:
        """Call the token contract's transfer (passes the guard)."""
        ok, why = self.guard.check(to, amount, self.guard.token_cap, "TOKEN")
        if not ok:
            return {"ok": False, "blocked_by_guard": why}
        call = self.token.functions.transfer(Web3.to_checksum_address(to), int(amount * 10**18))
        # passing gasPrice -> build_transaction makes a legacy tx (same as send_eth)
        tx = call.build_transaction({**self._base(), "gas": 200_000})
        r = self._sign_send(tx)
        self.guard.log.append(("transfer_token", to, amount))
        return {"ok": True, "tx": r.transactionHash.hex(), "block": r.blockNumber}

    def _base(self) -> dict:
        """Common tx fields (legacy: use gasPrice)."""
        return {"from": self.acct.address,
                "nonce": self.w3.eth.get_transaction_count(self.acct.address),
                "gasPrice": self.w3.eth.gas_price, "chainId": self.w3.eth.chain_id}

    def _sign_send(self, tx: dict):
        signed = self.acct.sign_transaction(tx)
        return self.w3.eth.wait_for_transaction_receipt(
            self.w3.eth.send_raw_transaction(signed.raw_transaction))


# The "tool list" an agent / LLM sees (framework-agnostic; OpenClaw etc. wrap this in their own format)
TOOLS = [
    {"name": "get_eth_balance", "desc": "get an address's native ETH balance",
     "params": {"address": "0x..."}},
    {"name": "get_token_balance", "desc": "get an address's token balance",
     "params": {"address": "0x..."}},
    {"name": "send_eth", "desc": "send ETH to an address (subject to guard cap + whitelist)",
     "params": {"to": "0x...", "amount_eth": "float"}},
    {"name": "transfer_token", "desc": "call the token contract transfer (subject to guard)",
     "params": {"to": "0x...", "amount": "float"}},
]


# ---------------------------- Demo: an agent calls these tools ----------------------------
def _deploy_demo_token(w3, pk):
    acct = w3.eth.account.from_key(pk)
    T = w3.eth.contract(abi=ART["abi"], bytecode=ART["bytecode"])
    tx = T.constructor("Demo", "DEMO").build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 2_000_000, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id})
    r = w3.eth.wait_for_transaction_receipt(
        w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction))
    addr = r.contractAddress
    tok = w3.eth.contract(address=addr, abi=ART["abi"])
    mtx = tok.functions.mint(acct.address, 1000 * 10**18).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200_000, "gasPrice": w3.eth.gas_price, "chainId": w3.eth.chain_id})
    w3.eth.wait_for_transaction_receipt(
        w3.eth.send_raw_transaction(acct.sign_transaction(mtx).raw_transaction))
    return addr


def demo():
    RPC = os.getenv("RPC", "http://localhost:8545")
    PK = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    FRIEND = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"   # anvil account 1 (on whitelist)
    STRANGER = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"  # anvil account 2 (not whitelisted)

    w3 = Web3(Web3.HTTPProvider(RPC))
    token_addr = _deploy_demo_token(w3, PK)

    guard = Guard(eth_cap=2.0, token_cap=100.0, whitelist={Web3.to_checksum_address(FRIEND)})
    tools = ChainTools(RPC, PK, guard, token_addr)

    print("=" * 64)
    print("Guard: per-call <= 2 ETH / <= 100 tokens, whitelist = FRIEND only")
    print("=" * 64)
    print("Available tools:", [t["name"] for t in TOOLS])

    print("\nSimulate an agent requesting tool calls:")
    print(" 1) get_eth_balance(FRIEND) ->", tools.get_eth_balance(FRIEND))
    print(" 2) send_eth(FRIEND, 1.0)   ->", tools.send_eth(FRIEND, 1.0))          # whitelisted + within cap -> pass
    print(" 3) send_eth(FRIEND, 5.0)   ->", tools.send_eth(FRIEND, 5.0))          # over per-call cap -> blocked
    print(" 4) send_eth(STRANGER, 0.1) ->", tools.send_eth(STRANGER, 0.1))        # not whitelisted -> blocked
    print(" 5) transfer_token(FRIEND, 40) ->", tools.transfer_token(FRIEND, 40))  # pass
    print(" 6) get_token_balance(FRIEND) ->", tools.get_token_balance(FRIEND))

    print("\nTakeaways:")
    print("  - The agent only REQUESTS a tool call; before executing it passes the Guard (cap + whitelist).")
    print("  - Over-cap and stranger payments are blocked off-chain -- no transaction ever goes out.")
    print("  - Homework: wire these tools into your own agent (OpenClaw) so it does them within the guard.")
    print("=" * 64)


if __name__ == "__main__":
    demo()
