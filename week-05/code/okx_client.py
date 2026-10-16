"""OKX demo-trading client (shared). The req() helper, with the three gotchas sealed in here:
  1. Force IPv4 globally (the API whitelist is IPv4; an IPv6 egress gets rejected with 50110)
  2. Browser UA (the default Python-urllib UA is blocked by Cloudflare with 1010)
  3. HMAC-SHA256 signature = ts + METHOD + path (incl. ? query) + body
x-simulated-trading: 1 is hard-coded on private calls -- this only ever touches the demo market.
Stdlib only.
Credentials: export OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE in your shell first
(load them from the macOS keychain or a .env; never hard-code keys).
"""
import base64, hashlib, hmac, json, os, socket, time
import urllib.request, urllib.error

_orig_gai = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_gai(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

BASE = "https://www.okx.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _creds():
    try:
        return os.environ["OKX_API_KEY"], os.environ["OKX_SECRET"], os.environ["OKX_PASSPHRASE"]
    except KeyError:
        raise SystemExit("Missing OKX credentials: export OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE first")


def req(method, path, body="", private=True, demo=None):
    """private=False hits public market data: no signature, no key needed.
    demo: private endpoints ALWAYS hit the demo market; public endpoints read the LIVE
    market by default, and only read the DEMO market when demo=True.
    Gotcha (verified 2026-09-30): the demo market is a separate venue -- its own book,
    prices and funding rate, quite different from live. A program that places orders on
    demo must also read quotes/funding with demo=True, otherwise you're "trading in
    market B using market A's data"."""
    headers = {"Content-Type": "application/json", "User-Agent": UA}
    if demo:
        headers["x-simulated-trading"] = "1"
    if private:
        key, secret, passphrase = _creds()
        ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
        sign = base64.b64encode(
            hmac.new(secret.encode(), (ts + method + path + body).encode(), hashlib.sha256).digest()
        ).decode()
        headers.update({"OK-ACCESS-KEY": key, "OK-ACCESS-SIGN": sign, "OK-ACCESS-TIMESTAMP": ts,
                        "OK-ACCESS-PASSPHRASE": passphrase, "x-simulated-trading": "1"})
    r = urllib.request.Request(BASE + path, data=body.encode() if body else None,
                               method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        return {"code": str(e.code), "msg": f"HTTP {e.code}: {raw[:200]}", "data": []}
    except Exception as e:
        return {"code": "-1", "msg": f"{type(e).__name__}: {e}", "data": []}
