"""Locally verify that a hidden-input signer derives the original bot address.

This utility does not load chain.py, contact an RPC, sign a transaction, or
write the entered key to disk. It prints only the final match verdict.
"""
import getpass
import hmac
import sys
import warnings

from eth_account import Account

TARGET_ADDRESS = "0xB03B27ea60D9fcc73366bd0ECB41945E91307209"


def _address_bytes(address):
    if not isinstance(address, str) or len(address) != 42 or not address.startswith("0x"):
        raise ValueError("invalid address")
    return bytes.fromhex(address[2:])


def signer_matches_target(private_key):
    """Derive locally and compare raw address bytes (case-insensitive)."""
    try:
        derived_address = Account.from_key(private_key).address
        return hmac.compare_digest(
            _address_bytes(derived_address), _address_bytes(TARGET_ADDRESS)
        )
    except Exception:
        return False


def main():
    # Refuse non-terminal input so the key can never be read from a pipe or
    # echoed by a fallback prompt. Treat getpass's no-echo warning as failure.
    if not sys.stdin.isatty():
        print("不匹配")
        return 1
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            private_key = getpass.getpass(prompt="", stream=sys.stderr).strip()
        matched = signer_matches_target(private_key)
        del private_key
    except Exception:
        matched = False
    print("匹配" if matched else "不匹配")
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
