"""Offline tests for the pure decision logic and dry-run adapter guard."""

import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("strategy_under_test", HERE / "strategy.py")
STRATEGY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STRATEGY)

WAD = 10**18
WALLET = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"


def view(pool_a, pool_b, balance=1_000 * WAD):
    return {
        "reserves": {"PoolA": pool_a, "PoolB": pool_b},
        "wallet": {"address": WALLET, "tusdc": balance},
    }


class DecisionTests(unittest.TestCase):
    def test_detects_liquid_spread_and_keeps_wallet_identity(self):
        signal = STRATEGY.decide(view(
            {"max": 100 * WAD, "usdc": 200_000 * WAD},
            {"max": 100 * WAD, "usdc": 220_000 * WAD},
        ))
        self.assertTrue(signal["hit"])
        self.assertEqual(signal["buy_pool"], "PoolA")
        self.assertEqual(signal["sell_pool"], "PoolB")
        self.assertEqual(signal["wallet_address"], WALLET)
        self.assertGreater(signal["amount_in"], 0)
        self.assertLessEqual(signal["amount_in"], 1_000 * WAD)

    def test_equal_prices_do_not_clear_fee_and_profit_threshold(self):
        signal = STRATEGY.decide(view(
            {"max": 100 * WAD, "usdc": 200_000 * WAD},
            {"max": 100 * WAD, "usdc": 200_000 * WAD},
        ))
        self.assertFalse(signal["hit"])

    def test_liquidity_floor_blocks_signal(self):
        signal = STRATEGY.decide(view(
            {"max": 100 * WAD, "usdc": 999 * WAD},
            {"max": 100 * WAD, "usdc": 2_000 * WAD},
        ))
        self.assertFalse(signal["hit"])
        self.assertFalse(signal["liquid"])

    def test_missing_wallet_balance_fails_closed(self):
        signal = STRATEGY.decide({"reserves": {}, "wallet": {"address": WALLET}})
        self.assertFalse(signal["hit"])
        self.assertIn("invalid view", signal["line"])

    def test_amount_out_uses_integer_rounding(self):
        out = STRATEGY.amount_out(1 * WAD, 100 * WAD, 200 * WAD)
        self.assertEqual(type(out), int)
        self.assertGreater(out, 0)

    def test_adapter_fire_is_fail_closed(self):
        fake_chain = types.ModuleType("chain")
        fake_chain.ADDR = {}
        fake_chain.CHAIN_ID = 84532
        fake_chain.at = lambda *_args: None
        fake_chain.erc20 = lambda *_args: None
        fake_chain.w3 = types.SimpleNamespace()
        adapter_spec = importlib.util.spec_from_file_location(
            "adapter_under_test", HERE / "zhenzhenfang_strategy_adapter.py"
        )
        adapter = importlib.util.module_from_spec(adapter_spec)
        with patch.dict(sys.modules, {"chain": fake_chain}):
            adapter_spec.loader.exec_module(adapter)
        with self.assertRaisesRegex(RuntimeError, "dry-run only"):
            adapter.fire({"hit": True})


if __name__ == "__main__":
    unittest.main()
