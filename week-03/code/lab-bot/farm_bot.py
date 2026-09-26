"""farm_bot.py — FarmBot (mine & dump), on its own wallet.

Watch this bot's staked LP position. When enough FARM has accrued, harvest it
(deposit(pid, 0) claims pending) and sell it for tUSDC on the FARM/tUSDC pool.
Profit = tUSDC received. Signs as its own wallet so the P&L is isolated.
"""
import sys, time
from chain import contract, at, ADDR, erc20, send, ensure_allowance, acct_of, load_bot_key

NAME = "farm-dump"
WAD = 10 ** 18
PID = 0
KEY = load_bot_key(NAME)          # this bot's own wallet
ME = acct_of(KEY).address
STAKER = ME                        # harvest our own stake
MIN_FARM = 1 * WAD                 # harvest only if pending > 1 FARM


def scan():
    chef = contract("MasterChef")
    pend = chef.functions.pendingFarm(PID, STAKER).call()
    return {"hit": pend >= MIN_FARM, "pending": pend / WAD,
            "line": f"pending FARM {pend/WAD:,.3f}"}


def fire(s):
    chef = contract("MasterChef")
    pool = at(ADDR["FarmPool"], "SimpleAMM")   # fresh FARM/tUSDC pool, token0=FARM
    farm, usdc = erc20("FARM"), erc20("tUSDC")
    me = ME
    u_before = usdc.functions.balanceOf(me).call()
    f_before = farm.functions.balanceOf(me).call()
    send(chef.functions.deposit(PID, 0), key=KEY)              # harvest (claims pending)
    # sell only the newly-harvested FARM; poll past RPC read lag
    harvested = 0
    for _ in range(12):
        harvested = farm.functions.balanceOf(me).call() - f_before
        if harvested > 0:
            break
        time.sleep(0.5)
    if harvested <= 0:
        raise RuntimeError("harvest landed but FARM balance still stale")
    ensure_allowance("FARM", ADDR["FarmPool"], key=KEY)
    rcpt = send(pool.functions.swap0For1(harvested), key=KEY)  # FARM -> tUSDC
    got = 0
    for _ in range(12):
        got = usdc.functions.balanceOf(me).call() - u_before
        if got > 0:
            break
        time.sleep(0.5)
    return {"tx": rcpt.transactionHash.hex(), "profit": got / WAD, "dumped_FARM": harvested / WAD}


if __name__ == "__main__":
    s = scan()
    print(f"[{NAME}] {s['line']} -> {'HIT' if s['hit'] else 'skip'}")
    if s["hit"] and "--live" in sys.argv:
        print("  firing...", fire(s))
