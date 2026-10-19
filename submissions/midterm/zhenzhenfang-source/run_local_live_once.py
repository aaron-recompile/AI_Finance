"""One-tick Arena LIVE launcher with hidden, process-local signer input.

This launcher never reads .env files and never enables course/allowance gates.
It calls the repository orchestrator exactly once with live=True. Do not run
unless the operator intends to review and authorize one 1 tUSDC -> MAX swap.
"""

import argparse
import getpass
import importlib
import os
from pathlib import Path
import sys
import warnings

from eth_account import Account
from web3 import Web3

HERE = Path(__file__).resolve().parent


def _find_repo_root():
    for candidate in (HERE, *HERE.parents):
        if (candidate / "week-03" / "code" / "lab-bot").is_dir():
            return candidate
    return None


REPO_ROOT = _find_repo_root()
LAB = REPO_ROOT / "week-03" / "code" / "lab-bot" if REPO_ROOT else Path("/nonexistent")
WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"
ADAPTER = "zhenzhenfang_strategy_adapter"


def _matches_target(private_key):
    try:
        derived = bytes.fromhex(Account.from_key(private_key).address[2:])
        expected = bytes.fromhex(WALLET[2:])
        return derived == expected
    except Exception:
        return False


def _read_hidden_key():
    if not sys.stdin.isatty():
        raise RuntimeError("interactive hidden signer input is required")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass("Original wallet signer (hidden): ", stream=sys.stderr).strip()
    except Exception:
        raise RuntimeError("hidden signer input unavailable") from None


def main():
    parser = argparse.ArgumentParser(description="One-tick, one-shot local Arena LIVE runner")
    parser.add_argument("--output", type=Path, default=HERE / "live_state.json")
    args = parser.parse_args()

    if not LAB.is_dir():
        parser.error("week-03/code/lab-bot was not found")
    if os.environ.get("COURSE_TEST_SWAP_AUTHORIZED") != "YES":
        parser.error("COURSE_TEST_SWAP_AUTHORIZED=YES is required; this script will not set it")
    if os.environ.get("AGENT_KEY") or os.environ.get("PRIVATE_KEY"):
        parser.error("unset inherited signer variables; this script only accepts hidden input")
    configured_address = os.environ.get("AGENT_ADDRESS")
    if configured_address:
        try:
            if Web3.to_checksum_address(configured_address) != Web3.to_checksum_address(WALLET):
                parser.error("configured AGENT_ADDRESS does not match the designated wallet")
        except ValueError:
            parser.error("configured AGENT_ADDRESS is malformed")

    private_key = _read_hidden_key()
    if not _matches_target(private_key):
        del private_key
        raise RuntimeError("signer=MISMATCH; no Arena tick or transaction was started")

    os.environ["AGENT_KEY"] = private_key
    os.environ["AGENT_ADDRESS"] = Web3.to_checksum_address(WALLET)
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(LAB))
    sys.argv = ["orchestrator.py", "--only", ADAPTER, "--live", "--interval", "12"]
    try:
        orchestrator = importlib.import_module("orchestrator")
        orchestrator.STATE = str(args.output)
        orchestrator.PNL = str(args.output.with_name("live_pnl.log"))
        state = orchestrator.tick(live=True, n=1)
        if state.get("mode") != "LIVE" or len(state.get("bots", [])) != 1:
            raise RuntimeError("unexpected orchestrator state")
        bot = state["bots"][0]
        if bot.get("name") != "zhenzhenfang-liquidity-aware":
            raise RuntimeError("unexpected strategy module loaded")
        if (not bot.get("fired") or not bot.get("last_tx")
                or bot.get("receipt_verified") is not True
                or bot.get("fire_status") != "success"):
            status = bot.get("fire_status", "unknown")
            detail = bot.get("fire_detail", "no outcome detail recorded")
            outcome_tx = bot.get("outcome_tx")
            raise RuntimeError(
                "one LIVE tick did not record a receipt-verified success "
                f"(status={status}; detail={detail}; outcome_tx={outcome_tx}); "
                "inspect live_state.json and the chain before starting another run"
            )
        print(state)
        print(f"LIVE state saved: {args.output}")
        return 0
    finally:
        os.environ.pop("AGENT_KEY", None)
        os.environ.pop("AGENT_ADDRESS", None)
        del private_key


if __name__ == "__main__":
    raise SystemExit(main())
