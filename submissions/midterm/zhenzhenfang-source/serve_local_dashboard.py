"""Serve an explicitly selected local Arena state snapshot (dry-run or live)."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import tempfile

HERE = Path(__file__).resolve().parent


def _find_repo_root():
    for candidate in (HERE, *HERE.parents):
        if (candidate / "week-03" / "code" / "lab-bot").is_dir():
            return candidate
    raise RuntimeError("repository week-03/code/lab-bot directory was not found")


REPO_ROOT = _find_repo_root()
LAB = REPO_ROOT / "week-03" / "code" / "lab-bot"
STATE_FILES = {"dry-run": "dry_run_state.json", "live": "live_state.json"}
WEBROOT = Path(tempfile.gettempdir()) / "zhenzhenfang_local_arena"
PORT = 8010


def selected_state_path(mode, submission_dir=HERE):
    if mode not in STATE_FILES:
        raise ValueError("mode must be 'dry-run' or 'live'")
    return Path(submission_dir) / STATE_FILES[mode]


def read_state(mode, submission_dir=HERE):
    path = selected_state_path(mode, submission_dir)
    if not path.is_file():
        raise FileNotFoundError(f"{path.name} is missing; no state fallback is permitted")
    with path.open(encoding="utf-8") as state_file:
        state = json.load(state_file)
    expected = "LIVE" if mode == "live" else "DRY-RUN"
    if not isinstance(state, dict) or state.get("mode") != expected:
        raise ValueError(f"{path.name} does not contain mode={expected}")
    if not isinstance(state.get("bots"), list):
        raise ValueError(f"{path.name} has an invalid bots list")
    if mode == "live":
        for bot in state["bots"]:
            if not isinstance(bot, dict):
                raise ValueError("live_state.json contains an invalid bot record")
            required = ("fires", "last_tx", "last_tx_verified", "receipt_verified",
                        "fire_status", "outcome_tx")
            if any(key not in bot for key in required):
                raise ValueError("live_state.json lacks verified-outcome fields; rerun the updated orchestrator")
            if type(bot["fires"]) is not int or bot["fires"] < 0:
                raise ValueError("live_state.json contains an invalid fire count")
            if bot["fires"] > 0 and (bot["last_tx_verified"] is not True or not bot["last_tx"]):
                raise ValueError("live_state.json has fires without a receipt-verified last transaction")
            if bot["last_tx"] and bot["last_tx_verified"] is not True:
                raise ValueError("live_state.json has an unverified Last TX")
            if bot["last_tx_verified"] is True and not bot["last_tx"]:
                raise ValueError("live_state.json marks a missing Last TX verified")
            for hash_field in ("last_tx", "outcome_tx"):
                tx_hash = bot[hash_field]
                if tx_hash is not None and (not isinstance(tx_hash, str)
                                            or re.fullmatch(r"0x[0-9a-fA-F]{64}", tx_hash) is None):
                    raise ValueError(f"live_state.json has an invalid {hash_field} format")
            if bot["receipt_verified"] is True and bot["fire_status"] != "success":
                raise ValueError("live_state.json has inconsistent receipt status")
            if bot["fire_status"] == "success" and (bot["fires"] < 1
                                                       or bot["receipt_verified"] is not True
                                                       or bot["last_tx_verified"] is not True
                                                       or not bot["last_tx"]):
                raise ValueError("live_state.json marks an unverified transaction successful")
    return path, state


def prepare_webroot(mode, submission_dir=HERE, webroot=None):
    state_path, _state = read_state(mode, submission_dir)
    target = Path(webroot) if webroot else WEBROOT / mode
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "dashboard.html", target / "dashboard.html")
    # Snapshot only the explicitly selected runner output. LIVE never falls
    # back to a dry-run file, and the JSON mode was checked above.
    shutil.copyfile(state_path, target / "state.json")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=tuple(STATE_FILES), default="dry-run",
                        help="state source to serve; live reads live_state.json only")
    args = parser.parse_args(argv)
    try:
        target = prepare_webroot(args.mode)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    handler = partial(SimpleHTTPRequestHandler, directory=str(target))
    server = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    label = "LIVE snapshot from live_state.json" if args.mode == "live" else "DRY-RUN snapshot from dry_run_state.json"
    print(f"Local Arena Dashboard ({label}): http://localhost:{PORT}/dashboard.html", flush=True)
    print("Local dashboard only; not a verified course leaderboard. Press Ctrl-C to stop.", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
