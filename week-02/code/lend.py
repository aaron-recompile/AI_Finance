"""
Week 2 - Your own on-chain pawnshop: over-collateralized lending + liquidation (runnable sim)
Pure Python, no chain. First own the math of "health factor / liquidation".
Compare with lend-foundry/src/SimpleLend.sol -- same math, that one is an on-chain contract.

run:  python lend.py
"""
from __future__ import annotations
from dataclasses import dataclass

LIQ_THRESHOLD = 0.80   # liquidation threshold: only 80% of collateral value backs the debt
LIQ_BONUS = 1.10       # liquidation bonus: liquidator repays 1 unit of debt, seizes 1.1 of collateral


@dataclass
class Lend:
    """A minimal single-collateral / single-debt lending market. price is fed by an external 'oracle'."""
    price: float                       # 1 collateral = how much debt asset (e.g. 2000 USDC/ETH)
    collateral: float = 0.0            # deposited collateral (e.g. ETH)
    debt: float = 0.0                  # borrowed debt (e.g. USDC)

    def deposit(self, amount: float) -> None:
        self.collateral += amount

    def borrow(self, amount: float) -> None:
        self.debt += amount
        assert self.health_factor() >= 1.0, "borrow would be unhealthy, rejected"

    @property
    def collateral_value(self) -> float:
        return self.collateral * self.price

    def health_factor(self) -> float:
        """HF = collateral value * threshold / debt. No debt -> infinity (always safe)."""
        if self.debt == 0:
            return float("inf")
        return self.collateral_value * LIQ_THRESHOLD / self.debt

    def liquidate(self) -> tuple[float, float]:
        """When HF<1: repay all debt, seize collateral at a 110% discount. Returns (repaid, seized)."""
        assert self.health_factor() < 1.0, "healthy, cannot liquidate"
        repaid = self.debt
        seize = repaid * LIQ_BONUS / self.price
        seize = min(seize, self.collateral)
        self.collateral -= seize
        self.debt = 0
        return repaid, seize


def demo():
    print("=" * 60)
    print("(1) Open: deposit 1 ETH @ $2000, borrow 1000 USDC")
    m = Lend(price=2000)
    m.deposit(1)
    m.borrow(1000)
    print(f"    collateral value = ${m.collateral_value:,.0f}   debt = ${m.debt:,.0f}")
    print(f"    health factor HF = {m.health_factor():.2f}  (>1 safe)")

    print("\n(2) Limit: 1 ETH @ $2000, 80% threshold -> can back at most $1600 of debt")
    print("    borrow 1600 -> HF = 2000*0.8/1600 = 1.00 (edge); any more is rejected.")

    print("\n(3) Market drops: the oracle cuts ETH from $2000 to $1200")
    m.price = 1200
    hf = m.health_factor()
    print(f"    collateral value = ${m.collateral_value:,.0f}   HF = {hf:.2f}")
    print(f"    {'WARNING HF < 1: anyone can liquidate you!' if hf < 1 else 'still safe'}")

    print("\n(4) Liquidated: a liquidator repays your 1000 USDC, seizes collateral at a discount")
    repaid, seized = m.liquidate()
    print(f"    liquidator repaid {repaid:,.0f} USDC, seized {seized:.4f} ETH"
          f" (worth ${seized*1200:,.0f}; the extra 10% is their bonus)")
    print(f"    you have {m.collateral:.4f} ETH left, debt {m.debt:,.0f} USDC (cleared)")

    print("\n(5) Point: no bank calls you -- HF crosses 1 and a bot arrives in seconds,")
    print("    repays your debt and takes your collateral at a discount. That is on-chain liquidation.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
