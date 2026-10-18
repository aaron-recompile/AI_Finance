"""Mock tests for explicit dry-run/LIVE dashboard state selection."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "serve_local_dashboard_under_test", HERE / "serve_local_dashboard.py"
)
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)


class LiveDashboardTests(unittest.TestCase):
    def test_live_mode_serves_only_live_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dry = {"mode": "DRY-RUN", "bots": [{"last_tx": "dry-tx"}]}
            real_hash = "0x" + "cd" * 32
            live = {"mode": "LIVE", "bots": [{
                "fires": 1, "last_tx": real_hash, "last_tx_verified": True,
                "receipt_verified": True, "fire_status": "success", "outcome_tx": None,
            }]}
            (root / "dry_run_state.json").write_text(json.dumps(dry), encoding="utf-8")
            (root / "live_state.json").write_text(json.dumps(live), encoding="utf-8")
            path, state = SERVER.read_state("live", root)
            self.assertEqual(path.name, "live_state.json")
            self.assertEqual(state, live)

    def test_live_mode_never_falls_back_to_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dry_run_state.json").write_text(
                json.dumps({"mode": "DRY-RUN", "bots": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(FileNotFoundError, "no state fallback"):
                SERVER.read_state("live", root)

    def test_mode_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "live_state.json").write_text(
                json.dumps({"mode": "DRY-RUN", "bots": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "mode=LIVE"):
                SERVER.read_state("live", root)

    def test_live_unverified_fire_and_tx_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "live_state.json").write_text(json.dumps({
                "mode": "LIVE", "bots": [{
                    "fires": 1, "last_tx": "0x" + "ef" * 32, "last_tx_verified": False,
                    "receipt_verified": False, "fire_status": "unknown", "outcome_tx": "0x" + "ef" * 32,
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fires without a receipt-verified"):
                SERVER.read_state("live", root)

    def test_live_unknown_outcome_with_zero_successful_fires_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = {"mode": "LIVE", "bots": [{
                "fires": 0, "last_tx": None, "last_tx_verified": False,
                "receipt_verified": False, "fire_status": "unknown", "outcome_tx": "0x" + "12" * 32,
            }]}
            (root / "live_state.json").write_text(json.dumps(state), encoding="utf-8")
            _path, loaded = SERVER.read_state("live", root)
            self.assertEqual(loaded, state)

    def test_live_webroot_copies_only_the_validated_live_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            webroot = root / "web"
            live = {"mode": "LIVE", "bots": [{
                "fires": 1, "last_tx": "0x" + "34" * 32, "last_tx_verified": True,
                "receipt_verified": True, "fire_status": "success", "outcome_tx": None,
            }]}
            (root / "live_state.json").write_text(json.dumps(live), encoding="utf-8")
            target = SERVER.prepare_webroot("live", root, webroot)
            served = json.loads((target / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(target, webroot)
            self.assertEqual(served, live)

    def test_dashboard_labels_local_board_and_gates_last_tx_on_verified_receipt(self):
        html = (SERVER.LAB / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("not a verified course leaderboard", html)
        self.assertIn("b.last_tx_verified && b.last_tx", html)
        self.assertIn("['pending','unknown','failed'].includes(b.fire_status)", html)


if __name__ == "__main__":
    unittest.main()
