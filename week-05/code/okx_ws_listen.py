#!/usr/bin/env python3
"""Drill 6: OKX demo private WebSocket, live reports (read-only).

Connect to the demo private WS, log in, subscribe to the orders + account channels, and
print order state/fills and balance changes in real time. Places no orders. Ctrl-C to quit.

Dependency:  pip3 install websockets
Credentials: read OKX_API_KEY / OKX_SECRET / OKX_PASSPHRASE from the environment
How to run:  run this listener in one terminal, then place an order from another terminal
             (okx_orders.py); come back to this window to watch the live push -- this is
             "how a strategy knows it got filled".
"""
import asyncio, base64, hashlib, hmac, json, os, socket, time
import websockets

URL = "wss://wspap.okx.com:8443/ws/v5/private"

API_KEY = os.environ["OKX_API_KEY"]
SECRET = os.environ["OKX_SECRET"]
PASSPHRASE = os.environ["OKX_PASSPHRASE"]


def login_args():
    ts = str(int(time.time()))
    msg = ts + "GET" + "/users/self/verify"
    sign = base64.b64encode(
        hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).digest()
    ).decode()
    return {"apiKey": API_KEY, "passphrase": PASSPHRASE, "timestamp": ts, "sign": sign}


async def keepalive(ws):
    # OKX requires a periodic text "ping", otherwise it drops the connection after ~30s
    while True:
        await asyncio.sleep(20)
        try:
            await ws.send("ping")
        except Exception:
            return


def show_order(o):
    print(f"  [ORDER] {o.get('instId')} {o.get('side')} {o.get('ordType')} "
          f"state={o.get('state')} sz={o.get('sz')} fillSz={o.get('fillSz')} "
          f"avgPx={o.get('avgPx')} ordId={o.get('ordId')}")


def show_account(a):
    for d in a.get("details", []):
        if d.get("ccy") in ("USDT", "BTC", "ETH", "OKB"):
            print(f"  [ACCT] {d.get('ccy')}: bal={d.get('cashBal')} avail={d.get('availBal')}")


async def run_once():
    # family=AF_INET forces IPv4, otherwise OKX sees an IPv6 egress not on the whitelist and rejects login
    async with websockets.connect(URL, ping_interval=None, family=socket.AF_INET) as ws:
        await ws.send(json.dumps({"op": "login", "args": [login_args()]}))
        asyncio.create_task(keepalive(ws))
        async for raw in ws:
            if raw == "pong":
                continue
            m = json.loads(raw)
            ev = m.get("event")
            if ev == "login":
                if m.get("code") == "0":
                    print("login ok, subscribing to orders + account ...")
                    await ws.send(json.dumps({"op": "subscribe", "args": [
                        {"channel": "orders", "instType": "SPOT"},
                        {"channel": "account"},
                    ]}))
                else:
                    print("login failed:", m); return
            elif ev == "subscribe":
                print("subscribed:", m.get("arg"))
            elif ev == "error":
                print("error:", m)
            elif "data" in m:
                ch = m.get("arg", {}).get("channel")
                for d in m["data"]:
                    if ch == "orders":
                        show_order(d)
                    elif ch == "account":
                        show_account(d)


async def main():
    while True:
        try:
            print(f"connecting {URL} ...")
            await run_once()
            print("connection closed, reconnecting in 3s ...")
        except Exception as e:
            print(f"disconnected ({type(e).__name__}: {e}), reconnecting in 3s ...")
        await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye.")
