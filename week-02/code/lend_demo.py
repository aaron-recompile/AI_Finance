"""
Week 2 - Liquidation sweep (the "sweep" companion to il_demo.py)
Fix a position, sweep the collateral price, and see:
  (1) how the health factor falls as the price drops;
  (2) where the liquidation price is (HF exactly = 1);
  (3) how much extra you lose once liquidated.

run:  python lend_demo.py
Compare with: lend.py (single full-scenario), SimpleLend.sol (on-chain contract).
"""
from __future__ import annotations

LIQ_THRESHOLD = 0.80   # liquidation threshold
LIQ_BONUS = 1.10       # liquidation bonus (liquidator takes an extra 10%)


def health_factor(collateral: float, price: float, debt: float) -> float:
    if debt == 0:
        return float("inf")
    return collateral * price * LIQ_THRESHOLD / debt


def liquidation_price(collateral: float, debt: float) -> float:
    """Price where HF = 1: collateral * P * threshold = debt -> P = debt / (collateral*threshold)."""
    return debt / (collateral * LIQ_THRESHOLD)


def liquidation_loss(collateral: float, price: float, debt: float) -> tuple[float, float]:
    """On liquidation: liquidator repays debt, seizes collateral at 110%.
    Returns (collateral seized, value lost vs. repaying yourself at market)."""
    seized = min(debt * LIQ_BONUS / price, collateral)
    # if you repaid debt yourself at market, you'd only sell debt/price of collateral;
    # being liquidated costs you the extra 10% penalty
    fair = debt / price
    penalty_value = (seized - fair) * price
    return seized, penalty_value


def demo():
    collateral = 1.0     # deposit 1 ETH
    debt = 1000.0        # borrow 1000 USDC
    entry_price = 2000.0

    print("=" * 66)
    print(f"Position: {collateral:.0f} ETH collateral, {debt:,.0f} USDC debt, entry ${entry_price:,.0f}")
    print(f"Threshold {LIQ_THRESHOLD:.0%}  bonus {LIQ_BONUS:.0%}")
    lp = liquidation_price(collateral, debt)
    print(f"-> liquidation price (HF=1) = {debt:,.0f} / ({collateral:.0f} x {LIQ_THRESHOLD}) = ${lp:,.2f}")
    print("=" * 66)

    print("\n(1) Sweep: ETH price falling from 2000, watch HF and whether it's liquidatable")
    print(f"{'ETH price':>10} {'coll value':>11} {'HF':>7}   status")
    for price in (2000, 1600, 1400, 1250, 1200, 1000, 800):
        hf = health_factor(collateral, price, debt)
        status = "safe" if hf >= 1 else "LIQUIDATABLE"
        mark = "   <- liq price" if abs(price - lp) < 1 else ("   <- below liq price" if price < lp else "")
        print(f"{price:>10,.0f} {collateral*price:>11,.0f} {hf:>7.2f}   {status}{mark}")

    print("\n(2) Cost of being liquidated (example: price at $1200)")
    price = 1200
    seized, penalty = liquidation_loss(collateral, price, debt)
    print(f"    liquidator repays {debt:,.0f} USDC of debt, seizes {seized:.4f} ETH (worth ${seized*price:,.0f})")
    print(f"    if you had repaid at market you'd sell only {debt/price:.4f} ETH")
    print(f"    -> being liquidated cost you an extra {seized-debt/price:.4f} ETH ~ ${penalty:,.0f} (the 10% penalty)")

    print("\n(3) Points:")
    print("    - HF is a linear function of price: halve the price, halve the HF;")
    print("    - the liquidation price is computable in advance: P* = debt / (collateral x threshold);")
    print("    - liquidation is not just repaying -- you pay a penalty -> keep a buffer, don't borrow at HF=1.")
    print("=" * 66)


if __name__ == "__main__":
    demo()
