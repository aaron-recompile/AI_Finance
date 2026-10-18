"""Read-only adapter from the course orchestrator's scan/fire interface."""

import importlib.util
import os
from pathlib import Path

from web3 import Web3
from chain import ADDR, CHAIN_ID, at, erc20, w3

_STRATEGY_PATH = Path(__file__).with_name("strategy.py")
_SPEC = importlib.util.spec_from_file_location("zhenzhenfang_original_strategy", _STRATEGY_PATH)
_STRATEGY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_STRATEGY)

NAME = _STRATEGY.NAME
_TARGET_WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"


def _wallet_address():
    configured = os.environ.get("AGENT_ADDRESS", "")
    if not configured:
        raise RuntimeError("AGENT_ADDRESS is required for this wallet-read dry-run")
    try:
        address = Web3.to_checksum_address(configured)
        expected = Web3.to_checksum_address(_TARGET_WALLET)
    except Exception:
        raise RuntimeError("AGENT_ADDRESS is malformed") from None
    if address != expected:
        raise RuntimeError("AGENT_ADDRESS does not match the designated public wallet")
    return address


def _read_pool(name):
    pair = at(ADDR[name], "Pair")
    token0 = Web3.to_checksum_address(pair.functions.token0().call())
    token1 = Web3.to_checksum_address(pair.functions.token1().call())
    max_address = Web3.to_checksum_address(ADDR["MAX"])
    usdc_address = Web3.to_checksum_address(ADDR["tUSDC"])
    if {token0, token1} != {max_address, usdc_address}:
        raise RuntimeError(f"{name} does not contain exactly MAX and tUSDC")
    reserve0, reserve1 = pair.functions.getReserves().call()
    if token0 == max_address:
        max_reserve, usdc_reserve = reserve0, reserve1
    else:
        max_reserve, usdc_reserve = reserve1, reserve0
    if max_reserve <= 0 or usdc_reserve <= 0:
        raise RuntimeError(f"{name} has empty reserves")
    return {"max": int(max_reserve), "usdc": int(usdc_reserve)}


def scan():
    """Read Base Sepolia pool reserves and the designated wallet's tUSDC balance."""
    if w3.eth.chain_id != CHAIN_ID:
        raise RuntimeError(f"wrong chain: expected {CHAIN_ID}")
    address = _wallet_address()
    view = {
        "reserves": {name: _read_pool(name) for name in ("PoolA", "PoolB")},
        "wallet": {
            "address": address,
            "tusdc": int(erc20("tUSDC").functions.balanceOf(address).call()),
        },
    }
    return _STRATEGY.decide(view)


def fire(_signal):
    """Fail closed: this submitted adapter cannot sign or broadcast transactions."""
    raise RuntimeError("This adapter is dry-run only; no transaction was sent")
