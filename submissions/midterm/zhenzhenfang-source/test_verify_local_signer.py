"""Offline tests for the hidden-input signer address verifier."""
import contextlib
import io
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_local_signer as verifier


class SignerVerifierTests(unittest.TestCase):
    def test_compares_address_bytes_without_case_sensitivity(self):
        account = types.SimpleNamespace(address=verifier.TARGET_ADDRESS.lower())
        with patch.object(verifier.Account, "from_key", return_value=account):
            self.assertTrue(verifier.signer_matches_target("mock-input-only"))

    def test_rejects_different_derived_address(self):
        account = types.SimpleNamespace(address="0x0000000000000000000000000000000000000001")
        with patch.object(verifier.Account, "from_key", return_value=account):
            self.assertFalse(verifier.signer_matches_target("mock-input-only"))

    def test_rejects_invalid_key_or_address_without_details(self):
        with patch.object(verifier.Account, "from_key", side_effect=ValueError):
            self.assertFalse(verifier.signer_matches_target("mock-input-only"))
        with patch.object(
            verifier.Account, "from_key",
            return_value=types.SimpleNamespace(address="not-an-address"),
        ):
            self.assertFalse(verifier.signer_matches_target("mock-input-only"))

    def test_noninteractive_mode_does_not_prompt_or_read_input(self):
        output = io.StringIO()
        with patch.object(verifier.sys, "stdin", types.SimpleNamespace(isatty=lambda: False)), \
                patch.object(verifier.getpass, "getpass") as hidden_input, \
                contextlib.redirect_stdout(output):
            result = verifier.main()
        hidden_input.assert_not_called()
        self.assertEqual(output.getvalue(), "不匹配\n")
        self.assertEqual(result, 1)

    def test_success_prints_only_match_verdict(self):
        terminal = types.SimpleNamespace(isatty=lambda: True)
        output = io.StringIO()
        account = types.SimpleNamespace(address=verifier.TARGET_ADDRESS)
        with patch.object(verifier.sys, "stdin", terminal), \
                patch.object(verifier.getpass, "getpass", return_value="mock-input-only"), \
                patch.object(verifier.Account, "from_key", return_value=account), \
                contextlib.redirect_stdout(output):
            result = verifier.main()
        self.assertEqual(output.getvalue(), "匹配\n")
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
