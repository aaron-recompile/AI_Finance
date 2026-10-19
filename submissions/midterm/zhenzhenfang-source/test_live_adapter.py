"""Offline mocks for the Arena LIVE adapter; no RPC, signer, or broadcast."""

import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

from web3 import Web3

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(
    candidate for candidate in (HERE, *HERE.parents)
    if (candidate / "week-03" / "code" / "lab-bot").is_dir()
)
LAB = REPO_ROOT / "week-03" / "code" / "lab-bot"
sys.path.insert(0, str(LAB))

from chain import ADDR  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "zhenzhenfang_strategy_adapter", HERE / "zhenzhenfang_strategy_adapter.py"
)
ADAPTER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ADAPTER
SPEC.loader.exec_module(ADAPTER)

WAD = 10**18
WALLET = ADAPTER._TARGET_WALLET
ROUTER = Web3.to_checksum_address(ADDR["RouterA"])
PAIR = Web3.to_checksum_address(ADDR["PoolA"])
USDC = Web3.to_checksum_address(ADDR["tUSDC"])
MAX = Web3.to_checksum_address(ADDR["MAX"])


class FakeCall:
    def __init__(self, value):
        self.value = value

    def call(self):
        return self.value


class FakeFunctions:
    def __init__(self, allowance=WAD, balance=100 * WAD, gas_estimate=50_000):
        self.allowance_value = allowance
        self.balance_value = balance
        self.gas_estimate = gas_estimate
        self.swap_args = None

    def decimals(self):
        return FakeCall(18)

    def allowance(self, _owner, _spender):
        return FakeCall(self.allowance_value)

    def balanceOf(self, _owner):
        return FakeCall(self.balance_value)

    def swapExactTokensForTokens(self, *args):
        self.swap_args = args
        fn = MagicMock()
        fn.estimate_gas.return_value = self.gas_estimate
        fn._encode_transaction_data.return_value = "0x12345678"
        return fn


class FakeW3:
    def __init__(self):
        self.eth = types.SimpleNamespace(
            chain_id=84532,
            gas_price=2,
            contract=lambda **_kwargs: types.SimpleNamespace(
                functions=types.SimpleNamespace(decimals=lambda: FakeCall(18))
            ),
            get_code=lambda _address: b"\x01",
            get_balance=lambda _address: 10**18,
        )


def signal():
    return {
        "hit": True,
        "buy_pool": "PoolA",
        "sell_pool": "PoolB",
        "buy_router": "RouterA",
        "sell_router": "RouterB",
        "amount_in": WAD,
        "wallet_address": WALLET,
    }


def log(token, sender, recipient, value):
    return {
        "address": token,
        "topics": [bytes(ADAPTER._TRANSFER_TOPIC), ADAPTER._address_topic(sender),
                   ADAPTER._address_topic(recipient)],
        "data": value.to_bytes(32, "big"),
    }


class LiveAdapterTests(unittest.TestCase):
    def setUp(self):
        ADAPTER._send_attempted = False
        ADAPTER.w3 = FakeW3()
        ADAPTER.at = lambda _address, _kind: types.SimpleNamespace(
            functions=FakeFunctions()
        )
        ADAPTER.erc20 = lambda _name: types.SimpleNamespace(functions=FakeFunctions())
        ADAPTER.acct_of = lambda _key: types.SimpleNamespace(address=WALLET)
        ADAPTER._read_pool = lambda _name: {"usdc": 100 * WAD, "max": 10 * WAD}
        ADAPTER.scan = lambda: signal()
        self.orchestrator = types.ModuleType("orchestrator")
        self.orchestrator._ACTIVE_LIVE_BOT = ADAPTER
        self.modules_patch = patch.dict(sys.modules, {"orchestrator": self.orchestrator})
        self.modules_patch.start()
        self.env_patch = patch.dict(os.environ, {
            "AGENT_KEY": "mock-only-key",
            "AGENT_ADDRESS": WALLET,
            "COURSE_TEST_SWAP_AUTHORIZED": "YES",
        }, clear=True)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.modules_patch.stop()

    def test_manual_fire_without_orchestrator_live_context_refuses(self):
        self.orchestrator._ACTIVE_LIVE_BOT = None
        with self.assertRaisesRegex(RuntimeError, "orchestrator LIVE tick"):
            ADAPTER.fire(signal())

    def test_official_runner_context_requires_exact_run_py_module_and_live_flag(self):
        main_module = sys.modules["__main__"]
        runner = REPO_ROOT / "week-03" / "code" / "lab-bot" / "run.py"
        with patch.object(main_module, "__file__", str(runner)), \
                patch.object(sys, "argv", [str(runner), ADAPTER.__name__, "--live"]):
            self.assertTrue(ADAPTER._official_run_py_live_call())
        with patch.object(main_module, "__file__", str(runner)), \
                patch.object(sys, "argv", [str(runner), ADAPTER.__name__]):
            self.assertFalse(ADAPTER._official_run_py_live_call())
        with patch.object(main_module, "__file__", str(runner)), \
                patch.object(sys, "argv", [str(runner), "another_bot", "--live"]):
            self.assertFalse(ADAPTER._official_run_py_live_call())

    def test_official_runner_state_counts_only_receipt_verified_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter_file = Path(tmp) / "zhenzhenfang_strategy_adapter.py"
            with patch.object(ADAPTER, "__file__", str(adapter_file)):
                ADAPTER._write_official_runner_state(result={
                    "tx": "0x" + "ab" * 32,
                    "receipt_verified": True,
                    "line": "Verified mock result",
                })
            state = json.loads((Path(tmp) / "live_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["mode"], "LIVE")
        row = state["bots"][0]
        self.assertEqual(row["fires"], 1)
        self.assertTrue(row["receipt_verified"])
        self.assertEqual(row["last_tx"], "0x" + "ab" * 32)

        with tempfile.TemporaryDirectory() as tmp:
            adapter_file = Path(tmp) / "zhenzhenfang_strategy_adapter.py"
            with patch.object(ADAPTER, "__file__", str(adapter_file)):
                ADAPTER._write_official_runner_state(error=RuntimeError("pending"))
            state = json.loads((Path(tmp) / "live_state.json").read_text(encoding="utf-8"))
        row = state["bots"][0]
        self.assertEqual(row["fires"], 0)
        self.assertIsNone(row["last_tx"])
        self.assertFalse(row["receipt_verified"])
        self.assertEqual(row["fire_status"], "rejected")

    def test_fire_accepts_exact_official_live_runner_and_records_verified_state(self):
        self.orchestrator._ACTIVE_LIVE_BOT = None
        runner = REPO_ROOT / "week-03" / "code" / "lab-bot" / "run.py"
        receipt_result = {
            "tx": "0x" + "cd" * 32,
            "receipt_verified": True,
            "line": "Verified mock result",
        }
        main_module = sys.modules["__main__"]
        with patch.object(main_module, "__file__", str(runner)), \
                patch.object(sys, "argv", [str(runner), ADAPTER.__name__, "--live"]), \
                patch.object(ADAPTER, "_fire_once", return_value=receipt_result), \
                patch.object(ADAPTER, "_write_official_runner_state") as write_state:
            self.assertEqual(ADAPTER.fire(signal()), receipt_result)
        write_state.assert_called_once_with(result=receipt_result)

    def test_course_gate_is_preserved_and_not_auto_enabled(self):
        os.environ.pop("COURSE_TEST_SWAP_AUTHORIZED")
        with patch.object(ADAPTER, "send") as send_mock:
            with self.assertRaisesRegex(RuntimeError, "COURSE_TEST_SWAP_AUTHORIZED=YES"):
                ADAPTER.fire(signal())
        send_mock.assert_not_called()
        self.assertNotIn("COURSE_TEST_SWAP_AUTHORIZED", os.environ)

    def test_signer_mismatch_refuses_without_send(self):
        ADAPTER.acct_of = lambda _key: types.SimpleNamespace(
            address="0x0000000000000000000000000000000000000001"
        )
        with patch.object(ADAPTER, "send") as send_mock:
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                ADAPTER._execution_account()
        send_mock.assert_not_called()

    def test_minimum_output_is_positive_and_slippage_bounded(self):
        quote = 10_000
        self.assertEqual(ADAPTER._minimum_output(quote), 9_900)
        with self.assertRaisesRegex(RuntimeError, "quote is zero"):
            ADAPTER._minimum_output(0)

    def test_confirmation_rejects_noninteractive_terminal_without_reading_input(self):
        with patch.object(ADAPTER.sys.stdin, "isatty", return_value=False), \
                patch("builtins.input") as input_mock:
            with self.assertRaisesRegex(RuntimeError, "requires a terminal; no transaction was sent"):
                ADAPTER._confirm_proposal("proposal")
        input_mock.assert_not_called()

    def test_confirmation_accepts_exact_phrase_only(self):
        phrase = "SEND exact phrase"
        with patch.object(ADAPTER.sys.stdin, "isatty", return_value=True), \
                patch("builtins.input", return_value=phrase):
            self.assertIsNone(ADAPTER._confirm_proposal(phrase))
        with patch.object(ADAPTER.sys.stdin, "isatty", return_value=True), \
                patch("builtins.input", return_value=phrase + " "):
            with self.assertRaisesRegex(RuntimeError, "did not match; no transaction was sent"):
                ADAPTER._confirm_proposal(phrase)

    def test_confirmation_distinguishes_empty_and_eof_without_send(self):
        with patch.object(ADAPTER.sys.stdin, "isatty", return_value=True), \
                patch("builtins.input", return_value=""):
            with self.assertRaisesRegex(RuntimeError, "confirmation was empty; no transaction was sent"):
                ADAPTER._confirm_proposal("proposal")
        with patch.object(ADAPTER.sys.stdin, "isatty", return_value=True), \
                patch("builtins.input", side_effect=EOFError):
            with self.assertRaisesRegex(RuntimeError, "no confirmation was received.*no transaction was sent"):
                ADAPTER._confirm_proposal("proposal")

    def test_confirmation_mismatch_fails_before_send(self):
        with patch("builtins.input", return_value="wrong confirmation"), \
                patch.object(ADAPTER.sys.stdin, "isatty", return_value=True), \
                patch.object(ADAPTER, "send") as send_mock:
            with self.assertRaisesRegex(RuntimeError, "did not match; no transaction was sent"):
                ADAPTER.fire(signal())
        send_mock.assert_not_called()

    def test_gas_limit_buffer_obeys_hard_cap(self):
        self.assertEqual(ADAPTER._gas_limit(50_000), 60_000)
        with self.assertRaisesRegex(RuntimeError, "hard cap"):
            ADAPTER._gas_limit(700_000)

    def test_successful_mock_live_tick_records_single_leg_receipt(self):
        reserves = {"usdc": 100 * WAD, "max": 10 * WAD}
        quote = ADAPTER._STRATEGY.amount_out(WAD, reserves["usdc"], reserves["max"])
        min_out = ADAPTER._minimum_output(quote)
        calldata = "0x12345678"
        txhash = bytes.fromhex("ab" * 32)
        receipt = {
            "status": 1,
            "transactionHash": txhash,
            "blockNumber": 123,
            "gasUsed": 60_000,
            "logs": [log(USDC, WALLET, PAIR, WAD), log(MAX, PAIR, WALLET, min_out)],
        }
        ADAPTER.w3.eth.get_transaction = lambda _hash: {
            "from": WALLET,
            "to": ROUTER,
            "chainId": 84532,
            "value": 0,
            # Match Web3's HexBytes behavior: .hex() has no 0x prefix.
            "input": bytes.fromhex(calldata[2:]),
        }
        large_signal = signal()
        large_signal["amount_in"] = 50 * WAD
        ADAPTER.scan = lambda: large_signal
        router_functions = FakeFunctions()
        ADAPTER.at = lambda _address, _kind: types.SimpleNamespace(
            functions=router_functions
        )
        with patch.object(ADAPTER, "send", return_value=receipt) as send_mock, \
                patch("builtins.input", return_value=(
                    f"SEND 1 tUSDC TO {WALLET} VIA {ROUTER} MIN_OUT_BASE_UNITS {min_out}"
                )), \
                patch.object(ADAPTER.sys.stdin, "isatty", return_value=True):
            result = ADAPTER.fire(large_signal)
        send_mock.assert_called_once()
        self.assertEqual(send_mock.call_args.kwargs["key"], "mock-only-key")
        self.assertEqual(send_mock.call_args.kwargs["retries"], 1)
        self.assertEqual(router_functions.swap_args[0], WAD)
        self.assertEqual(router_functions.swap_args[1], min_out)
        self.assertEqual(result["profit"], 0)
        self.assertEqual(result["tx"], "0x" + "ab" * 32)
        self.assertTrue(result["receipt_verified"])
        self.assertEqual(result["fire_status"], "success")
        self.assertEqual(result["received_max"], min_out)
        self.assertIn("not a two-pool arbitrage", result["line"])
        with self.assertRaisesRegex(RuntimeError, "already attempted"):
            ADAPTER.fire(signal())

    def test_incomplete_transfer_verification_raises_unknown_not_success(self):
        reserves = {"usdc": 100 * WAD, "max": 10 * WAD}
        quote = ADAPTER._STRATEGY.amount_out(WAD, reserves["usdc"], reserves["max"])
        min_out = ADAPTER._minimum_output(quote)
        calldata = "0x12345678"
        receipt = {
            "status": 1,
            "transactionHash": bytes.fromhex("ef" * 32),
            "blockNumber": 124,
            "gasUsed": 60_000,
            "logs": [log(USDC, WALLET, PAIR, WAD), log(MAX, PAIR, WALLET, min_out - 1)],
        }
        ADAPTER.w3.eth.get_transaction = lambda _hash: {
            "from": WALLET, "to": ROUTER, "chainId": 84532, "value": 0,
            "input": bytes.fromhex(calldata[2:]),
        }
        large_signal = signal()
        large_signal["amount_in"] = 50 * WAD
        ADAPTER.scan = lambda: large_signal
        router_functions = FakeFunctions()
        ADAPTER.at = lambda _address, _kind: types.SimpleNamespace(functions=router_functions)
        with patch.object(ADAPTER, "send", return_value=receipt), \
                patch("builtins.input", return_value=(
                    f"SEND 1 tUSDC TO {WALLET} VIA {ROUTER} MIN_OUT_BASE_UNITS {min_out}"
                )), \
                patch.object(ADAPTER.sys.stdin, "isatty", return_value=True):
            with self.assertRaisesRegex(ADAPTER.FireOutcomeError, "verification is incomplete") as caught:
                ADAPTER.fire(large_signal)
        self.assertEqual(caught.exception.outcome_status, "unknown")
        self.assertEqual(caught.exception.tx, "0x" + "ef" * 32)

    def test_insufficient_allowance_never_approves_or_sends(self):
        ADAPTER.erc20 = lambda _name: types.SimpleNamespace(
            functions=FakeFunctions(allowance=0)
        )
        with patch.object(ADAPTER, "send") as send_mock:
            with self.assertRaisesRegex(RuntimeError, "no approval"):
                ADAPTER.fire(signal())
        send_mock.assert_not_called()

    def test_unacknowledged_infinite_allowance_refuses_without_send(self):
        ADAPTER.erc20 = lambda _name: types.SimpleNamespace(
            functions=FakeFunctions(allowance=2**256 - 1)
        )
        with patch.object(ADAPTER, "send") as send_mock:
            with self.assertRaisesRegex(RuntimeError, "unlimited allowance"):
                ADAPTER.fire(signal())
        send_mock.assert_not_called()

    def test_gas_estimate_over_hard_cap_refuses_without_send(self):
        ADAPTER.at = lambda _address, _kind: types.SimpleNamespace(
            functions=FakeFunctions(gas_estimate=700_000)
        )
        with patch.object(ADAPTER, "send") as send_mock, \
                patch("builtins.input") as input_mock:
            with self.assertRaisesRegex(RuntimeError, "hard cap"):
                ADAPTER.fire(signal())
        send_mock.assert_not_called()
        input_mock.assert_not_called()


class LiveLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runner_spec = importlib.util.spec_from_file_location(
            "live_once_under_test", HERE / "run_local_live_once.py"
        )
        cls.runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(cls.runner)

    def test_hidden_signer_match_is_address_byte_comparison(self):
        fake_account = types.SimpleNamespace(address=self.runner.WALLET.lower())
        with patch.object(self.runner.Account, "from_key", return_value=fake_account):
            self.assertTrue(self.runner._matches_target("mock-only-key"))

    def test_signer_mismatch_fails(self):
        fake_account = types.SimpleNamespace(
            address="0x0000000000000000000000000000000000000001"
        )
        with patch.object(self.runner.Account, "from_key", return_value=fake_account):
            self.assertFalse(self.runner._matches_target("mock-only-key"))

    def test_live_launcher_does_not_enable_course_gate(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(self.runner.sys, "argv", ["run_local_live_once.py"]), \
                patch.object(self.runner, "_read_hidden_key") as read_key, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.runner.main()
            read_key.assert_not_called()
            self.assertNotIn("COURSE_TEST_SWAP_AUTHORIZED", os.environ)

    def test_live_launcher_rejects_conflicting_configured_address(self):
        with patch.dict(os.environ, {
            "COURSE_TEST_SWAP_AUTHORIZED": "YES",
            "AGENT_ADDRESS": "0x0000000000000000000000000000000000000001",
        }, clear=True), \
                patch.object(self.runner.sys, "argv", ["run_local_live_once.py"]), \
                patch.object(self.runner, "_read_hidden_key") as read_key, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.runner.main()
            read_key.assert_not_called()


class OrchestratorLiveContextTests(unittest.TestCase):
    def test_only_live_tick_sets_adapter_fire_context(self):
        calls = []
        fake_bot = types.ModuleType("arena_fake_bot")
        fake_bot.NAME = "probe"
        fake_bot.REQUIRES_VERIFIED_RECEIPT = True
        fake_bot.scan = lambda: {"hit": True, "line": "mock hit"}
        fake_bot.fire = lambda _signal: (
            calls.append(orch._ACTIVE_LIVE_BOT is fake_bot)
            or {"tx": "0xmock", "profit": 0, "receipt_verified": True}
        )
        sys.modules[fake_bot.__name__] = fake_bot
        orch_spec = importlib.util.spec_from_file_location(
            "orchestrator", LAB / "orchestrator.py"
        )
        orch = importlib.util.module_from_spec(orch_spec)
        sys.modules["orchestrator"] = orch
        old_argv = sys.argv
        try:
            sys.argv = ["orchestrator.py", "--only", fake_bot.__name__]
            orch_spec.loader.exec_module(orch)
            with tempfile.TemporaryDirectory() as tmp:
                orch.STATE = str(Path(tmp) / "state.json")
                orch.PNL = str(Path(tmp) / "pnl.log")
                dry = orch.tick(live=False, n=1)
                self.assertEqual(dry["bots"][0]["fires"], 0)
                self.assertEqual(calls, [])
                live = orch.tick(live=True, n=2)
                self.assertEqual(calls, [True])
                self.assertEqual(live["bots"][0]["fires"], 1)
                self.assertEqual(live["bots"][0]["last_tx"], "0xmock")
                self.assertTrue(live["bots"][0]["receipt_verified"])
                self.assertTrue(live["bots"][0]["last_tx_verified"])
                self.assertEqual(live["bots"][0]["fire_status"], "success")
                self.assertIsNone(orch._ACTIVE_LIVE_BOT)
        finally:
            sys.argv = old_argv
            sys.modules.pop(fake_bot.__name__, None)
            sys.modules.pop("orchestrator", None)

    def test_unconfirmed_fire_stays_pending_then_unknown_and_never_counts(self):
        fake_bot = types.ModuleType("arena_uncertain_bot")
        fake_bot.NAME = "uncertain"
        fake_bot.REQUIRES_VERIFIED_RECEIPT = True
        fake_bot.scan = lambda: {"hit": True, "line": "mock hit"}
        observed = []

        def uncertain_fire(_signal):
            with open(orch.STATE, encoding="utf-8") as state_file:
                observed.append(json.load(state_file)["bots"][0])
            error = RuntimeError("receipt wait did not complete")
            error.outcome_status = "unknown"
            error.tx = "0x" + "ab" * 32
            raise error

        fake_bot.fire = uncertain_fire
        sys.modules[fake_bot.__name__] = fake_bot
        orch_spec = importlib.util.spec_from_file_location("orchestrator", LAB / "orchestrator.py")
        orch = importlib.util.module_from_spec(orch_spec)
        sys.modules["orchestrator"] = orch
        old_argv = sys.argv
        try:
            sys.argv = ["orchestrator.py", "--only", fake_bot.__name__]
            orch_spec.loader.exec_module(orch)
            with tempfile.TemporaryDirectory() as tmp:
                orch.STATE = str(Path(tmp) / "state.json")
                orch.PNL = str(Path(tmp) / "pnl.log")
                state = orch.tick(live=True, n=1)
            row = state["bots"][0]
            self.assertEqual(observed[0]["fire_status"], "pending")
            self.assertEqual(observed[0]["fires"], 0)
            self.assertEqual(row["fire_status"], "unknown")
            self.assertEqual(row["fires"], 0)
            self.assertIsNone(row["last_tx"])
            self.assertFalse(row["last_tx_verified"])
            self.assertEqual(row["outcome_tx"], "0x" + "ab" * 32)
            self.assertFalse(row["receipt_verified"])
        finally:
            sys.argv = old_argv
            sys.modules.pop(fake_bot.__name__, None)
            sys.modules.pop("orchestrator", None)


if __name__ == "__main__":
    unittest.main()
