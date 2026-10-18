"""Run one read-only tick through the repository's actual orchestrator."""

import argparse
import importlib
import json
import os
from pathlib import Path
import sys

from web3 import Web3

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1] / "week-03" / "code" / "lab-bot"
WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"
ADAPTER = "zhenzhenfang_strategy_adapter"


def main():
    parser = argparse.ArgumentParser(description="One-tick read-only local Arena run")
    parser.add_argument("--wallet", default=WALLET, help="public address only; no key is read")
    parser.add_argument("--output", type=Path, default=HERE / "dry_run_state.json")
    args = parser.parse_args()

    address = Web3.to_checksum_address(args.wallet)
    if address != Web3.to_checksum_address(WALLET):
        parser.error("this evidence runner is restricted to the designated public wallet")
    if not LAB.is_dir():
        parser.error("week-03/code/lab-bot was not found")

    # The adapter only needs this public address to read the wallet balance.
    os.environ["AGENT_ADDRESS"] = address
    sys.path.insert(0, str(LAB))
    sys.argv = ["orchestrator.py", "--only", ADAPTER, "--interval", "12"]

    orchestrator = importlib.import_module("orchestrator")
    orchestrator.STATE = str(args.output)
    orchestrator.PNL = str(args.output.with_name("dry_run_pnl.log"))
    state = orchestrator.tick(live=False, n=1)

    if state.get("mode") != "DRY-RUN" or len(state.get("bots", [])) != 1:
        raise RuntimeError("unexpected orchestrator state; refusing to record evidence")
    bot = state["bots"][0]
    if bot.get("name") != "zhenzhenfang-liquidity-aware":
        raise RuntimeError("unexpected strategy module loaded")
    if bot.get("line", "").startswith("scan err:"):
        raise RuntimeError("market/wallet read failed; no successful dry-run evidence")
    if bot.get("fires") != 0 or bot.get("last_tx") is not None:
        raise RuntimeError("dry-run unexpectedly contains a transaction record")

    print(json.dumps(state, indent=2))
    print(f"Dry-run state saved: {args.output}")


if __name__ == "__main__":
    main()
