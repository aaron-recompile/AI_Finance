"""
Week 2 - Your own Uniswap: the x*y=k constant-product market maker (runnable simulation)
Pure Python, no network / no chain. First own the math of "building a Uniswap" (the R1/R4 mental model).

run:  python amm.py
Later in the lab you will: (1) extend it (fees / liquidity) (2) advanced track: write it as Solidity and deploy.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AMM:
    """A constant-product pool holding two token reserves: x * y = k."""
    x: float          # reserve of token A (e.g. ETH)
    y: float          # reserve of token B (e.g. USDC)
    fee: float = 0.0  # fee rate (0.003 = 0.3%, Uniswap default)

    @property
    def k(self) -> float:
        return self.x * self.y

    @property
    def price(self) -> float:
        """How many B is 1 A worth (mid price = y/x)."""
        return self.y / self.x

    def swap_a_for_b(self, dx: float) -> float:
        """Put in dx of A, return how much B comes out. k stays constant (after fee)."""
        dx_eff = dx * (1 - self.fee)          # the fee stays in the pool
        # (x+dx_eff)*(y-dy) = k  ->  dy = y - k/(x+dx_eff)
        new_x = self.x + dx_eff
        dy = self.y - self.k / new_x
        # actually update reserves (the fee portion enters the pool too, so add dx, not dx_eff)
        self.x += dx
        self.y -= dy
        return dy

    def quote_a_for_b(self, dx: float) -> float:
        """Quote only, do not mutate the pool (used to compute slippage)."""
        dx_eff = dx * (1 - self.fee)
        return self.y - self.k / (self.x + dx_eff)


def slippage_bps(pool: AMM, dx: float) -> float:
    """Slippage (bps) of a swap: how far the actual average fill deviates from the mid price."""
    mid = pool.price                      # 1 A = mid B
    dy = pool.quote_a_for_b(dx)
    avg = dy / dx                          # actual: how much B per A
    return (mid - avg) / mid * 1e4         # less out = more slippage


def demo():
    print("=" * 56)
    print("(1) Build a pool: 100 ETH / 200,000 USDC  -> 1 ETH = 2000 USDC")
    pool = AMM(x=100, y=200_000, fee=0.003)
    print(f"    k = {pool.k:,.0f}   mid price = {pool.price:,.1f} USDC/ETH")

    print("\n(2) Slippage grows with trade size (selling ETH for USDC)")
    for dx in (0.1, 1, 5, 20):
        s = slippage_bps(pool, dx)
        dy = pool.quote_a_for_b(dx)
        print(f"    sell {dx:>5} ETH -> get {dy:>12,.2f} USDC   avg {dy/dx:>9,.1f}   slippage {s:6.1f} bps")

    print("\n(3) Execute one real swap: sell 5 ETH")
    before = pool.price
    got = pool.swap_a_for_b(5)
    print(f"    got {got:,.2f} USDC; pool now {pool.x:.2f} ETH / {pool.y:,.2f} USDC")
    print(f"    price moved {before:,.1f} -> {pool.price:,.1f} (a big trade pushes the price)")

    print("\n(4) Takeaway: small trades ~ no slippage, big trades slide fast along the curve -- that's x*y=k.")
    print("=" * 56)


if __name__ == "__main__":
    demo()
