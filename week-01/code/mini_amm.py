"""
Week 1 - Session 2: your first AMM (20 lines, pure math, off-chain)
In Session 1 you issued an asset; now the question: who trades it? Nobody is waiting.
The AMM's answer = a pool + one formula, x*y=k. Here we write that formula and break it.
(This is just a calculator; in Week 2 you turn it into a real contract, deploy it, use cast.)

run:  python mini_amm.py
"""


class MiniAMM:
    def __init__(self, x, y):        # x = ETH reserve, y = USDC reserve
        self.x, self.y = x, y

    @property
    def price(self):                 # how many USDC is 1 ETH (mid price)
        return self.y / self.x

    def swap_eth_for_usdc(self, dx):  # put in dx ETH, return USDC out
        k = self.x * self.y
        dy = self.y - k / (self.x + dx)   # keep the product x*y = k
        self.x += dx
        self.y -= dy
        return dy


def demo():
    pool = MiniAMM(x=100, y=200_000)      # 100 ETH / 200,000 USDC -> 1 ETH = 2000
    print(f"Pool: {pool.x} ETH / {pool.y:,} USDC   mid price {pool.price:,.0f}\n")

    print("Sell different amounts of ETH, watch the average fill (fresh pool each time):")
    for dx in (1, 5, 20):
        p = MiniAMM(100, 200_000)
        got = p.swap_eth_for_usdc(dx)
        print(f"  sell {dx:>2} ETH -> get {got:>10,.1f} USDC   avg {got/dx:>8,.1f}   price after {p.price:>7,.1f}")

    print("\nTakeaway: the more you sell, the further the average drifts below 2000 and")
    print("          the price after gets pushed down -- that is SLIPPAGE: the geometry")
    print("          of the x*y=k curve, not a fee anyone charges you.")
    print("Next (Week 2): turn these 20 lines into a real Solidity contract, deploy it, use cast.")


if __name__ == "__main__":
    demo()
