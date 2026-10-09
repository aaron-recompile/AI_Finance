# ---------------------------------------------------------------
# Dry-run: see exactly what "one order request" looks like (real signature, not submitted, no funds needed)
#   How: subclass Exchange and replace the final "send it" _post_action with "print it"
# Setup: put your TESTNET key in a local .env (see .env.example):  PRIVATE_KEY=0x...
# Run:  python hl_dryrun.py
# ---------------------------------------------------------------
import json
from pathlib import Path
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

HERE = Path(__file__).resolve().parent


class DryExchange(Exchange):
    """Assembles + signs exactly like the real Exchange, just prints instead of POSTing."""
    def _post_action(self, action, signature, nonce):
        print("\n=== this is the SIGNED order request that would be sent (dry-run, not submitted) ===")
        print(json.dumps({"action": action, "nonce": nonce, "signature": signature}, indent=2, default=str))
        return {"status": "dry-run (not submitted)"}


pk = next(l.split("=", 1)[1].strip() for l in (HERE / ".env").read_text().splitlines() if l.startswith("PRIVATE_KEY="))
wallet = Account.from_key(pk)
print("wallet:", wallet.address)

ex = DryExchange(wallet, constants.TESTNET_API_URL)   # init pulls meta once (read-only)
# a BTC limit buy 0.001 @ $30,000 (GTC) -- really signed, but never actually sent
ex.order("BTC", True, 0.001, 30000, {"limit": {"tif": "Gtc"}})
