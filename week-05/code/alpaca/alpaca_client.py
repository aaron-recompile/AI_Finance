"""Alpaca PAPER client (shared). Compare with okx_client.py:
  OKX    = key+secret+passphrase, the secret never leaves, HMAC-sign every call, demo via a header
  Alpaca = key+secret sent as two headers, no signature; paper mode via a DIFFERENT domain (paper-api)
Two domains: trading paper-api.alpaca.markets (orders/account) and market data data.alpaca.markets (quotes/bars)
Credentials: run `source alpaca_env.sh` first. Stdlib only.
"""
import json, os, urllib.request, urllib.error, urllib.parse

TRADE = "https://paper-api.alpaca.markets"   # hard-coded paper, not read from env, so it can't point at live by mistake
DATA = "https://data.alpaca.markets"


def _headers():
    try:
        kid, sec = os.environ["APCA_API_KEY_ID"], os.environ["APCA_API_SECRET_KEY"]
    except KeyError:
        raise SystemExit("Missing Alpaca credentials: run `source alpaca_env.sh` first")
    if not kid.startswith("PK"):
        raise SystemExit("Key ID does not start with PK -- looks like a live key, refusing to run")
    return {"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec, "Content-Type": "application/json"}


def req(method, path, body=None, params=None, base=TRADE):
    url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=_headers())
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        # Compare with OKX: Alpaca uses HTTP status codes for success/failure (403/404/422);
        # OKX always returns 200 + code/sCode.
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"message": raw[:200]}
