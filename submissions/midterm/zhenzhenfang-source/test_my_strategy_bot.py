"""Offline-only fire() guard tests. No Web3 provider or signing is used."""
import builtins
from contextlib import redirect_stdout
import importlib.util
import io
import os
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

from web3 import Web3

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "my_strategy_bot.py"
WAD = 10**18
WALLET = "0x1234567890123456789012345678901234567890"
MOCK_KEY = "offline-test-only-not-a-private-key"


class Call:
    def __init__(self, value):
        self.value = value

    def call(self):
        return self.value() if callable(self.value) else self.value


class FakeEth:
    chain_id = 84532
    gas_price = 10

    def get_code(self, address):
        return b"mock contract code"

    def get_balance(self, address):
        return NATIVE_BALANCE

    def contract(self, **kwargs):
        class Functions:
            def decimals(self):
                return Call(18)

        return types.SimpleNamespace(functions=Functions())

    def get_transaction(self, tx_hash):
        return {
            "from": WALLET,
            "to": ADDR["RouterA"],
            "chainId": 84532,
            "value": 0,
            "input": bytes.fromhex(ROUTER.functions.last._encode_transaction_data()[2:]),
        }


class FakeTokenFunctions:
    def __init__(self, name):
        self.name = name

    def balanceOf(self, _who):
        return Call(lambda: BALANCES[self.name][0])

    def allowance(self, _who, _spender):
        return Call(lambda: BALANCES[self.name][1])


class FakeToken:
    def __init__(self, name):
        self.functions = FakeTokenFunctions(name)


class FakeSwap:
    def __init__(self, args):
        self.args = args

    def estimate_gas(self, _tx):
        return GAS_ESTIMATE

    def _encode_transaction_data(self):
        return "0xabcdef1234"


class FakeRouterFunctions:
    last = None

    def swapExactTokensForTokens(self, *args):
        self.last = FakeSwap(args)
        return self.last


class FakeRouter:
    functions = FakeRouterFunctions()


ADDR = {
    "MAX": "0x22201343039BB6418546978b447a45ee49f8dAa5",
    "tUSDC": "0x6797beC4DC1D4444Fe81790c47e9FB91e491Ac69",
    "PoolA": "0xEf12cfd16d5e7903b837b2EfECBcdb1A0b5349D8",
    "PoolB": "0x07a45F3560d1bbF708027D9CcD8Ac95FBcaaD73d",
    "RouterA": "0x2fc7C313bf38f0af4D92E8bE7347500D39174b82",
    "RouterB": "0x19272Cae94B8e3BCd7d6752823F40b925C5dad3C",
}
BALANCES = {"tUSDC": [10 * WAD, 10 * WAD], "MAX": [0, 0]}
GAS_ESTIMATE = 100_000
NATIVE_BALANCE = 10**18
TUSDC_SPENT = WAD
MAX_RECEIVED = 2 * 10**15
ROUTER = FakeRouter()
SENT = []


def fake_account(key):
    if key != MOCK_KEY:
        raise ValueError("invalid mock key")
    return types.SimpleNamespace(address=WALLET)


def fake_send(fn, **kwargs):
    SENT.append((fn, kwargs))
    BALANCES["tUSDC"][0] -= TUSDC_SPENT
    BALANCES["MAX"][0] += MAX_RECEIVED
    return types.SimpleNamespace(
        status=1,
        transactionHash=types.SimpleNamespace(hex=lambda: "0x" + "ab" * 32),
        blockNumber=7,
        gasUsed=100_000,
        effectiveGasPrice=10,
    )


FAKE_CHAIN = types.ModuleType("chain")
FAKE_CHAIN.ADDR = ADDR
FAKE_CHAIN.CHAIN_ID = 84532
FAKE_CHAIN.acct_of = fake_account
FAKE_CHAIN.erc20 = lambda name: FakeToken(name)
FAKE_CHAIN.w3 = types.SimpleNamespace(eth=FakeEth())
FAKE_CHAIN.at = lambda _address, _abi: ROUTER
FAKE_CHAIN.send = fake_send
sys.modules["chain"] = FAKE_CHAIN
spec = importlib.util.spec_from_file_location("strategy_under_test", SOURCE)
BOT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BOT)
BOT.scan = lambda: {
    "hit": True, "buy_pool": "PoolA", "sell_pool": "PoolB",
    "buy_router": "RouterA", "sell_router": "RouterB", "amount_in": WAD,
}
BOT._read_pool = lambda name: {"name": name, "max": 100 * WAD, "usdc": 100_000 * WAD}
BOT._token_decimals = lambda _address: 18


class FireGuardTests(unittest.TestCase):
    def setUp(self):
        global GAS_ESTIMATE, NATIVE_BALANCE, TUSDC_SPENT, MAX_RECEIVED
        BALANCES["tUSDC"][:] = [10 * WAD, 10 * WAD]
        BALANCES["MAX"][:] = [0, 0]
        GAS_ESTIMATE = 100_000
        NATIVE_BALANCE = 10**18
        TUSDC_SPENT = WAD
        MAX_RECEIVED = 2 * 10**15
        SENT.clear()
        BOT._send_attempted = False
        FAKE_CHAIN.w3.eth.chain_id = 84532
        FAKE_CHAIN.w3.eth.gas_price = 10
        for name in ("AGENT_KEY", "AGENT_ADDRESS", BOT.COURSE_AUTH_ENV,
                     BOT.UNLIMITED_ALLOWANCE_ACK_ENV):
            os.environ.pop(name, None)
        self.snapshot = {
            "hit": True, "buy_pool": "PoolA", "sell_pool": "PoolB",
            "buy_router": "RouterA", "sell_router": "RouterB", "amount_in": WAD,
        }

    def configure_wallet(self):
        os.environ["AGENT_KEY"] = MOCK_KEY
        os.environ["AGENT_ADDRESS"] = WALLET
        os.environ[BOT.COURSE_AUTH_ENV] = "YES"

    def test_missing_key_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "AGENT_KEY is unset"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_mismatched_wallet_is_refused(self):
        os.environ["AGENT_KEY"] = MOCK_KEY
        os.environ["AGENT_ADDRESS"] = "0x0000000000000000000000000000000000000001"
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_malformed_key_is_refused(self):
        os.environ["AGENT_KEY"] = "malformed-mock-key"
        os.environ["AGENT_ADDRESS"] = WALLET
        with self.assertRaisesRegex(RuntimeError, "malformed"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_incomplete_or_stale_route_signal_is_refused(self):
        self.configure_wallet()
        stale = dict(self.snapshot)
        stale["sell_router"] = "RouterA"
        with self.assertRaisesRegex(RuntimeError, "signal is incomplete"):
            BOT.fire(stale)
        self.assertEqual(SENT, [])
        self.assertFalse(BOT._send_attempted)

    def test_missing_bot_specific_course_action_gate_is_refused(self):
        os.environ["AGENT_KEY"] = MOCK_KEY
        os.environ["AGENT_ADDRESS"] = WALLET
        with self.assertRaisesRegex(RuntimeError, "Bot-specific course-action gate"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_insufficient_allowance_is_refused_without_approval(self):
        self.configure_wallet()
        BALANCES["tUSDC"][1] = 0
        with self.assertRaisesRegex(RuntimeError, "No approval was sent"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_unacknowledged_unlimited_allowance_is_refused_without_send(self):
        self.configure_wallet()
        BALANCES["tUSDC"][1] = BOT.UINT256_MAX
        with self.assertRaisesRegex(RuntimeError, "requires separate local owner acknowledgement"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_wrong_chain_is_refused(self):
        self.configure_wallet()
        FAKE_CHAIN.w3.eth.chain_id = 1
        with self.assertRaisesRegex(RuntimeError, "Wrong chain ID"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_unexpected_decimals_are_refused(self):
        self.configure_wallet()
        original = BOT._token_decimals
        BOT._token_decimals = lambda _address: 6
        try:
            with self.assertRaisesRegex(RuntimeError, "Unexpected token decimals"):
                BOT.fire(self.snapshot)
        finally:
            BOT._token_decimals = original
        self.assertEqual(SENT, [])

    def test_insufficient_tusdc_balance_is_refused(self):
        self.configure_wallet()
        BALANCES["tUSDC"][0] = 0
        with self.assertRaisesRegex(RuntimeError, "lacks the test-swap tUSDC"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_noninteractive_execution_is_refused(self):
        self.configure_wallet()

        class NonInteractive:
            def isatty(self):
                return False

        with patch("sys.stdin", NonInteractive()):
            with self.assertRaisesRegex(RuntimeError, "Interactive approval"):
                BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_rejected_approval_does_not_send(self):
        self.configure_wallet()

        class InteractiveTerminal:
            def isatty(self):
                return True

        with patch("sys.stdin", InteractiveTerminal()), patch.object(
            builtins, "input", return_value="NO"
        ), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "not approved"):
                BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_gas_limit_buffer_is_capped_before_approval_or_send(self):
        global GAS_ESTIMATE
        self.configure_wallet()
        GAS_ESTIMATE = 700_000  # 20% buffer exceeds the 800,000 hard cap.
        with self.assertRaisesRegex(RuntimeError, "exceeds the configured cap"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_insufficient_native_gas_is_refused(self):
        global NATIVE_BALANCE
        self.configure_wallet()
        NATIVE_BALANCE = 0
        with self.assertRaisesRegex(RuntimeError, "maximum estimated gas"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_approved_mock_swap_uses_min_output_and_verifies_receipt(self):
        self.configure_wallet()
        BALANCES["tUSDC"][1] = BOT.UINT256_MAX
        os.environ[BOT.UNLIMITED_ALLOWANCE_ACK_ENV] = "YES"

        class InteractiveTerminal:
            def isatty(self):
                return True

        phrase = (
            f"SEND 1.000000 tUSDC TO {WALLET} VIA {ADDR['RouterA']} "
            f"MIN_OUT_BASE_UNITS {BOT._minimum_output(BOT.amount_out(WAD, 100_000 * WAD, 100 * WAD))}"
        )
        prompts = []

        def approve_exact_proposal(prompt):
            prompts.append(prompt)
            return phrase

        printed = io.StringIO()
        with patch("sys.stdin", InteractiveTerminal()), patch.object(
            builtins, "input", side_effect=approve_exact_proposal
        ), redirect_stdout(printed):
            result = BOT.fire(self.snapshot)

        self.assertEqual(len(SENT), 1)
        fn, kwargs = SENT[0]
        self.assertEqual(kwargs["key"], MOCK_KEY)
        self.assertEqual(kwargs["gas_price"], 10)
        self.assertLessEqual(kwargs["gas"], BOT.MAX_GAS_LIMIT)
        self.assertEqual(fn.args[0], WAD)
        self.assertGreater(fn.args[1], 0)  # never amountOutMin=0
        self.assertEqual(fn.args[2:], (ADDR["tUSDC"], ADDR["MAX"], WALLET))
        self.assertIn(f"VIA {ADDR['RouterA']} MIN_OUT_BASE_UNITS {fn.args[1]}", phrase)
        self.assertEqual(result["proposal"]["amount_out_min"], fn.args[1])
        self.assertEqual(result["proposal"]["gas_limit_cap"], BOT.MAX_GAS_LIMIT)
        self.assertEqual(result["proposal"]["max_gas_cost_wei"], kwargs["gas"] * kwargs["gas_price"])
        self.assertIn(f"amountOutMin (100 bps below quote)", printed.getvalue())
        self.assertIn(f"Configured gas limit cap: {BOT.MAX_GAS_LIMIT}", printed.getvalue())
        self.assertEqual(prompts, [f"To authorize this exact swap, type: {phrase}\n> "])
        self.assertEqual(result["block"], 7)
        self.assertEqual(result["spent_tUSDC"], WAD)
        self.assertEqual(result["received_MAX"], 2 * 10**15)
        self.assertEqual(result["actual_gas_cost_wei"], 1_000_000)
        self.assertIn("not an arbitrage", result["line"])

        # A runner loop may see the same HIT again. The module latch prevents
        # a second send, even if the caller reuses the original signal.
        with self.assertRaisesRegex(RuntimeError, "already attempted a transaction"):
            BOT.fire(self.snapshot)
        self.assertEqual(len(SENT), 1)

    def test_ambiguous_send_failure_latches_and_refuses_retry(self):
        self.configure_wallet()
        BALANCES["tUSDC"][1] = BOT.UINT256_MAX
        os.environ[BOT.UNLIMITED_ALLOWANCE_ACK_ENV] = "YES"

        class InteractiveTerminal:
            def isatty(self):
                return True

        phrase = (
            f"SEND 1.000000 tUSDC TO {WALLET} VIA {ADDR['RouterA']} "
            f"MIN_OUT_BASE_UNITS {BOT._minimum_output(BOT.amount_out(WAD, 100_000 * WAD, 100 * WAD))}"
        )
        with patch("sys.stdin", InteractiveTerminal()), patch.object(
            builtins, "input", return_value=phrase
        ), patch.object(BOT, "send", side_effect=RuntimeError("mock ambiguous send")), \
                redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "mock ambiguous send"):
                BOT.fire(self.snapshot)
        self.assertTrue(BOT._send_attempted)
        with self.assertRaisesRegex(RuntimeError, "already attempted a transaction"):
            BOT.fire(self.snapshot)
        self.assertEqual(SENT, [])

    def test_post_transaction_verification_requires_exact_input_spend(self):
        global TUSDC_SPENT
        self.configure_wallet()
        TUSDC_SPENT = WAD // 2
        phrase = (
            f"SEND 1.000000 tUSDC TO {WALLET} VIA {ADDR['RouterA']} "
            f"MIN_OUT_BASE_UNITS {BOT._minimum_output(BOT.amount_out(WAD, 100_000 * WAD, 100 * WAD))}"
        )

        class InteractiveTerminal:
            def isatty(self):
                return True

        with patch("sys.stdin", InteractiveTerminal()), patch.object(
            builtins, "input", return_value=phrase
        ), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "balance deltas failed"):
                BOT.fire(self.snapshot)
        self.assertEqual(len(SENT), 1)

    def test_post_transaction_verification_rejects_output_below_minimum(self):
        global MAX_RECEIVED
        self.configure_wallet()
        MAX_RECEIVED = 1
        phrase = (
            f"SEND 1.000000 tUSDC TO {WALLET} VIA {ADDR['RouterA']} "
            f"MIN_OUT_BASE_UNITS {BOT._minimum_output(BOT.amount_out(WAD, 100_000 * WAD, 100 * WAD))}"
        )

        class InteractiveTerminal:
            def isatty(self):
                return True

        with patch("sys.stdin", InteractiveTerminal()), patch.object(
            builtins, "input", return_value=phrase
        ), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "balance deltas failed"):
                BOT.fire(self.snapshot)
        self.assertEqual(len(SENT), 1)


if __name__ == "__main__":
    unittest.main()
