"""Arena adapter for the original liquidity-aware strategy.

The strategy still models a cross-pool spread, but this adapter executes only
one bounded tUSDC -> MAX leg. It is not an atomic arbitrage executor.
"""

import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

from web3 import Web3
from chain import ADDR, ABI, CHAIN_ID, acct_of, at, erc20, send, w3

_STRATEGY_PATH = Path(__file__).with_name("strategy.py")
_SPEC = importlib.util.spec_from_file_location("zhenzhenfang_original_strategy", _STRATEGY_PATH)
_STRATEGY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_STRATEGY)


def _find_repo_root(start=None):
    start = Path(start or __file__).resolve()
    for candidate in (start.parent, *start.parents):
        if (candidate / "week-03" / "code" / "lab-bot").is_dir():
            return candidate
    raise RuntimeError("repository week-03/code/lab-bot directory was not found")


_REPO_ROOT = _find_repo_root()

NAME = _STRATEGY.NAME
REQUIRES_VERIFIED_RECEIPT = True
_TARGET_WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"
WAD = 10**18
BPS = 10_000
TEST_SWAP_USDC = 1 * WAD
MAX_SWAP_USDC = 1 * WAD
MAX_SLIPPAGE_BPS = 100
GAS_LIMIT_BUFFER_BPS = 2_000
MAX_GAS_LIMIT = 800_000
COURSE_AUTH_ENV = "COURSE_TEST_SWAP_AUTHORIZED"
UNLIMITED_ALLOWANCE_ACK_ENV = "ALLOW_UNLIMITED_ALLOWANCE_CONFIRMED"
_send_attempted = False
_fire_lock = threading.Lock()

_DECIMALS_ABI = [{
    "name": "decimals", "type": "function", "stateMutability": "view",
    "inputs": [], "outputs": [{"type": "uint8"}],
}]
_TRANSFER_TOPIC = Web3.keccak(text="Transfer(address,address,uint256)")
_ROUTER_FOR_POOL = {"PoolA": "RouterA", "PoolB": "RouterB"}


class FireOutcomeError(RuntimeError):
    """A send was attempted, but its final on-chain outcome is not verified."""

    def __init__(self, message, outcome_status="unknown", tx=None):
        super().__init__(message)
        self.outcome_status = outcome_status
        self.tx = tx


def _hash_from_error(error):
    import re
    match = re.search(r"0x[a-fA-F0-9]{64}", str(error))
    return match.group(0) if match else None


def _wallet_address():
    configured = os.environ.get("AGENT_ADDRESS", "")
    if not configured:
        raise RuntimeError("AGENT_ADDRESS is required")
    try:
        address = Web3.to_checksum_address(configured)
        expected = Web3.to_checksum_address(_TARGET_WALLET)
    except Exception:
        raise RuntimeError("AGENT_ADDRESS is malformed") from None
    if address != expected:
        raise RuntimeError("AGENT_ADDRESS does not match the designated wallet")
    return address


def _execution_account():
    key = os.environ.get("AGENT_KEY", "")
    if not key:
        raise RuntimeError("AGENT_KEY is unset; execution refused")
    if os.environ.get("PRIVATE_KEY"):
        raise RuntimeError("PRIVATE_KEY fallback is forbidden; execution refused")
    address = _wallet_address()
    try:
        account = acct_of(key)
    except Exception:
        raise RuntimeError("AGENT_KEY is malformed; execution refused") from None
    if account.address != address:
        raise RuntimeError("AGENT_KEY does not match AGENT_ADDRESS; execution refused")
    return key, address


def _active_orchestrator_live_call():
    orchestrator = sys.modules.get("orchestrator")
    this_module = sys.modules.get(__name__)
    return (orchestrator is not None and this_module is not None
            and getattr(orchestrator, "_ACTIVE_LIVE_BOT", None) is this_module)


def _official_run_py_live_call():
    """Recognize only the repository's documented single-bot LIVE runner."""
    main_module = sys.modules.get("__main__")
    runner = _REPO_ROOT / "week-03" / "code" / "lab-bot" / "run.py"
    try:
        invoked_path = Path(sys.argv[0]).resolve()
        main_path = Path(getattr(main_module, "__file__", "")).resolve()
    except (OSError, TypeError, ValueError):
        return False
    return (invoked_path == runner.resolve() and main_path == runner.resolve()
            and len(sys.argv) > 1 and sys.argv[1] == __name__
            and "--live" in sys.argv)


def _write_official_runner_state(result=None, error=None):
    """Persist only this runner's verified result to the explicit LIVE state file."""
    verified = result is not None and result.get("receipt_verified") is True
    tx = result.get("tx") if verified else getattr(error, "tx", None)
    row = {
        "name": NAME,
        "hit": True,
        "line": result.get("line", "") if verified else str(error or "LIVE outcome unknown"),
        "pnl": 0,
        "fires": 1 if verified else 0,
        "last_tx": tx if verified else None,
        "fired": verified,
        "receipt_verified": verified,
        "last_tx_verified": verified,
        "fire_status": "success" if verified else getattr(error, "outcome_status", "rejected"),
        "outcome_tx": None if verified else tx,
        "fire_detail": result.get("line", "") if verified else str(error or "LIVE outcome unknown"),
    }
    state = {"updated": time.strftime("%H:%M:%S"), "tick": 1,
             "mode": "LIVE", "bots": [row], "total_pnl": 0}
    target = Path(__file__).with_name("live_state.json")
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


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
    """Read Base Sepolia pool reserves and the designated wallet's balance."""
    if w3.eth.chain_id != CHAIN_ID:
        raise RuntimeError(f"wrong chain: expected {CHAIN_ID}")
    address = _wallet_address()
    view = {
        "reserves": {name: _read_pool(name) for name in ("PoolA", "PoolB")},
        "wallet": {"address": address,
                   "tusdc": int(erc20("tUSDC").functions.balanceOf(address).call())},
    }
    return _STRATEGY.decide(view)


def _minimum_output(quoted_out):
    if quoted_out <= 0:
        raise RuntimeError("quote is zero; execution refused")
    amount_out_min = quoted_out * (BPS - MAX_SLIPPAGE_BPS) // BPS
    if amount_out_min <= 0:
        raise RuntimeError("amountOutMin is zero; execution refused")
    return amount_out_min


def _gas_limit(estimate):
    if estimate <= 0:
        raise RuntimeError("gas estimate is invalid; execution refused")
    limit = max(estimate + 10_000,
                (estimate * (BPS + GAS_LIMIT_BUFFER_BPS) + BPS - 1) // BPS)
    if limit > MAX_GAS_LIMIT:
        raise RuntimeError("gas estimate exceeds hard cap; execution refused")
    return limit


def _decimals(token_address):
    contract = w3.eth.contract(address=Web3.to_checksum_address(token_address),
                               abi=_DECIMALS_ABI)
    return int(contract.functions.decimals().call())


def _address_topic(address):
    return bytes.fromhex(Web3.to_checksum_address(address)[2:]).rjust(32, b"\x00")


def _normalize_hex_data(value):
    """Return 0x-prefixed lowercase hex for RPC bytes or hex strings.

    HexBytes.hex() in the installed Web3 stack omits the 0x prefix, while
    contract calldata encoders include it. Normalize both sides before comparing.
    """
    if isinstance(value, str):
        encoded = value if value.startswith("0x") else "0x" + value
    else:
        encoded = Web3.to_hex(bytes(value))
    return encoded.lower()


def _transfer_deltas(receipt, token_in, token_out, wallet):
    wallet_topic = _address_topic(wallet)
    spent = received = 0
    for log in receipt["logs"]:
        topics = [bytes(topic) for topic in log["topics"]]
        if len(topics) != 3 or topics[0] != bytes(_TRANSFER_TOPIC):
            continue
        token_address = Web3.to_checksum_address(log["address"])
        sender, recipient = topics[1], topics[2]
        data = log["data"]
        amount = int.from_bytes(bytes(data), "big") if not isinstance(data, str) else int(data, 16)
        if token_address == Web3.to_checksum_address(token_in) and sender == wallet_topic:
            spent += amount
        if token_address == Web3.to_checksum_address(token_out) and recipient == wallet_topic:
            received += amount
    return spent, received


def _confirm_proposal(proposal):
    """Require an exact, visible confirmation on an interactive terminal."""
    if not sys.stdin.isatty():
        raise RuntimeError("interactive transaction confirmation requires a terminal; no transaction was sent")
    print("Confirmation phrase (type exactly, without the surrounding quotes):", flush=True)
    print(proposal, flush=True)
    try:
        entered = input("Confirm by typing the phrase above and pressing Enter: ")
    except EOFError:
        raise RuntimeError("no confirmation was received (input closed); no transaction was sent") from None
    except KeyboardInterrupt:
        raise RuntimeError("transaction confirmation was cancelled; no transaction was sent") from None
    if entered == "":
        raise RuntimeError("confirmation was empty; no transaction was sent")
    if entered != proposal:
        raise RuntimeError("transaction confirmation did not match; no transaction was sent")


def fire(signal):
    """Execute one guarded swap from an orchestrator tick or official run.py LIVE call."""
    global _send_attempted
    if not _fire_lock.acquire(blocking=False):
        raise RuntimeError("another fire() call is active; execution refused")
    try:
        if _send_attempted:
            raise RuntimeError("one-shot execution already attempted in this process")
        orchestrator_call = _active_orchestrator_live_call()
        official_runner_call = _official_run_py_live_call()
        if not (orchestrator_call or official_runner_call):
            raise RuntimeError("fire() requires orchestrator LIVE tick or official run.py --live")
        # Latch immediately, including preflight/approval failures, so the loop
        # cannot make a second transaction attempt in the same process.
        _send_attempted = True
        try:
            result = _fire_once(signal)
        except Exception as exc:
            if official_runner_call:
                try:
                    _write_official_runner_state(error=exc)
                except OSError as state_error:
                    raise FireOutcomeError(
                        "LIVE outcome could not be written to dashboard state",
                        outcome_status=getattr(exc, "outcome_status", "unknown"),
                        tx=getattr(exc, "tx", None),
                    ) from state_error
            raise
        if official_runner_call:
            try:
                _write_official_runner_state(result=result)
            except OSError as state_error:
                raise FireOutcomeError(
                    "receipt was verified, but LIVE dashboard state could not be written",
                    outcome_status="unknown", tx=result.get("tx"),
                ) from state_error
        return result
    finally:
        _fire_lock.release()


def _fire_once(signal):
    if not isinstance(signal, dict) or not signal.get("hit"):
        raise RuntimeError("no active strategy signal; execution refused")
    if os.environ.get(COURSE_AUTH_ENV) != "YES":
        raise RuntimeError(f"{COURSE_AUTH_ENV}=YES is required; gate was not enabled")
    key, wallet = _execution_account()
    if w3.eth.chain_id != CHAIN_ID:
        raise RuntimeError(f"wrong chain ID; expected {CHAIN_ID}")

    fresh = scan()
    fields = ("buy_pool", "sell_pool", "buy_router", "sell_router", "amount_in")
    if not fresh.get("hit") or any(signal.get(field) != fresh.get(field) for field in fields):
        raise RuntimeError("signal is stale or route/size changed; execution refused")
    if fresh.get("wallet_address", "").lower() != wallet.lower():
        raise RuntimeError("strategy signal wallet mismatch; execution refused")

    pool_name = fresh["buy_pool"]
    router_name = fresh["buy_router"]
    if pool_name not in _ROUTER_FOR_POOL or _ROUTER_FOR_POOL[pool_name] != router_name:
        raise RuntimeError("unsupported pool/router mapping; execution refused")
    # This deliberately executes only the strategy's buy leg, capped at 1 tUSDC.
    if type(fresh["amount_in"]) is not int or fresh["amount_in"] < TEST_SWAP_USDC:
        raise RuntimeError("strategy size is below the fixed 1 tUSDC test amount")
    amount_in = TEST_SWAP_USDC
    if amount_in <= 0 or amount_in > MAX_SWAP_USDC:
        raise RuntimeError("swap amount exceeds the fixed cap; execution refused")

    router_address = Web3.to_checksum_address(ADDR[router_name])
    pair_address = Web3.to_checksum_address(ADDR[pool_name])
    token_in = Web3.to_checksum_address(ADDR["tUSDC"])
    token_out = Web3.to_checksum_address(ADDR["MAX"])
    for label, contract_address in (("router", router_address), ("pair", pair_address),
                                    ("tUSDC", token_in), ("MAX", token_out)):
        if not w3.eth.get_code(contract_address):
            raise RuntimeError(f"no contract code at configured {label}; execution refused")
    if _decimals(token_in) != 18 or _decimals(token_out) != 18:
        raise RuntimeError("unexpected token decimals; expected 18")

    reserves = _read_pool(pool_name)
    quoted_out = _STRATEGY.amount_out(amount_in, reserves["usdc"], reserves["max"])
    amount_out_min = _minimum_output(quoted_out)
    usdc = erc20("tUSDC")
    allowance = int(usdc.functions.allowance(wallet, router_address).call())
    balance = int(usdc.functions.balanceOf(wallet).call())
    if balance < amount_in:
        raise RuntimeError("insufficient tUSDC balance; execution refused")
    if allowance < amount_in:
        raise RuntimeError("insufficient existing allowance; no approval will be sent")
    if allowance == 2**256 - 1 and os.environ.get(UNLIMITED_ALLOWANCE_ACK_ENV) != "YES":
        raise RuntimeError("unlimited allowance requires separate local acknowledgement")

    router = at(router_address, "Router")
    swap_fn = router.functions.swapExactTokensForTokens(
        amount_in, amount_out_min, token_in, token_out, wallet
    )
    try:
        estimated_gas = int(swap_fn.estimate_gas({"from": wallet}))
        gas_limit = _gas_limit(estimated_gas)
        gas_price = int(w3.eth.gas_price)
        max_gas_cost = gas_limit * gas_price
        native_balance = int(w3.eth.get_balance(wallet))
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError("gas estimate or preflight read failed; execution refused") from None
    if native_balance < max_gas_cost:
        raise RuntimeError("insufficient native balance for maximum gas cost")

    proposal = (
        f"SEND 1 tUSDC TO {wallet} VIA {router_address} "
        f"MIN_OUT_BASE_UNITS {amount_out_min}"
    )
    print("ONE-LEG TEST SWAP — NOT A TWO-POOL ARBITRAGE")
    print(f"Base Sepolia chain ID: {CHAIN_ID}; wallet: {wallet}")
    print(f"Route: {pool_name}/{router_name}, tUSDC -> MAX; amount: 1 tUSDC")
    print(f"Quote: {quoted_out} MAX base units (assumed {_STRATEGY.SWAP_FEE_BPS} bps router fee); amountOutMin: {amount_out_min}")
    print(f"Slippage cap: {MAX_SLIPPAGE_BPS} bps; gas: estimate {estimated_gas}, limit {gas_limit}/{MAX_GAS_LIMIT}")
    print(f"Maximum gas cost: {max_gas_cost} wei; no approval will be sent")
    _confirm_proposal(proposal)

    # Revalidate moving conditions after the operator reviews the proposal.
    if w3.eth.chain_id != CHAIN_ID or int(w3.eth.gas_price) != gas_price:
        raise RuntimeError("chain or gas price changed after proposal")
    if int(usdc.functions.balanceOf(wallet).call()) < amount_in:
        raise RuntimeError("tUSDC balance changed after proposal")
    if int(usdc.functions.allowance(wallet, router_address).call()) < amount_in:
        raise RuntimeError("allowance changed after proposal")
    if int(w3.eth.get_balance(wallet)) < max_gas_cost:
        raise RuntimeError("native balance changed after proposal")
    current_reserves = _read_pool(pool_name)
    new_quote = _STRATEGY.amount_out(amount_in, current_reserves["usdc"],
                                    current_reserves["max"])
    if new_quote < amount_out_min:
        raise RuntimeError("pool quote moved below amountOutMin after proposal")

    # Explicit signer; one send attempt; never call ensure_allowance or funder defaults.
    try:
        receipt = send(swap_fn, gas=gas_limit, retries=1, key=key, gas_price=gas_price)
    except Exception as exc:
        message = str(exc)
        tx_hash = _hash_from_error(exc)
        status = "failed" if "tx reverted on-chain" in message.lower() else "unknown"
        raise FireOutcomeError("send attempted; receipt outcome is " + status,
                               outcome_status=status, tx=tx_hash) from None

    raw_hash = receipt.get("transactionHash")
    tx_hash = _normalize_hex_data(raw_hash)
    try:
        if int(receipt["status"]) != 1:
            raise ValueError("receipt status is not success")
        tx = w3.eth.get_transaction(raw_hash)
        calldata = _normalize_hex_data(swap_fn._encode_transaction_data())
        actual_input = _normalize_hex_data(tx["input"])
        if (Web3.to_checksum_address(tx["from"]) != wallet
                or Web3.to_checksum_address(tx["to"]) != router_address
                or int(tx.get("chainId", -1)) != CHAIN_ID
                or int(tx.get("value", 0)) != 0
                or actual_input != calldata):
            raise ValueError("mined transaction identity/calldata verification failed")
        spent, received = _transfer_deltas(receipt, token_in, token_out, wallet)
        if spent != amount_in or received < amount_out_min:
            raise ValueError("receipt Transfer events do not meet swap limits")
    except Exception:
        raise FireOutcomeError("transaction mined or returned, but receipt verification is incomplete",
                               outcome_status="unknown", tx=tx_hash) from None

    return {
        "tx": tx_hash,
        "receipt_verified": True,
        "fire_status": "success",
        "profit": 0,
        "line": "Verified one-leg tUSDC -> MAX swap; not a two-pool arbitrage.",
        "wallet": wallet,
        "amount_in": amount_in,
        "amount_out_min": amount_out_min,
        "received_max": received,
        "gas_used": int(receipt["gasUsed"]),
        "block": int(receipt["blockNumber"]),
    }
