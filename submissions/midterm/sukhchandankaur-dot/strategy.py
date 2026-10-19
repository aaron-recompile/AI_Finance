"""
Track B Strategy: Dynamic Mean-Reversion & Slippage-Protected Swap
Author: Sukhchandan Kaur
"""

class CustomStrategy:
    def __init__(self, mispricing_threshold=0.015, max_slippage=0.01):
        self.mispricing_threshold = mispricing_threshold
        self.max_slippage = max_slippage

    def calculate_fair_price(self, view):
        reserves = view.get("reserves", {})
        reserve0 = reserves.get("reserve0", 0)
        reserve1 = reserves.get("reserve1", 0)

        if reserve0 == 0 or reserve1 == 0:
            return None

        return reserve1 / reserve0

    def decide(self, view):
        balances = view.get("wallet", {}).get("balances", {})
        spot_price = self.calculate_fair_price(view)
        
        if spot_price is None:
            return None

        reference_price = view.get("oracle_price", spot_price)
        divergence = (spot_price - reference_price) / reference_price

        # If pool is undervalued beyond threshold -> Buy/Swap
        if divergence < -self.mispricing_threshold:
            eth_balance = balances.get("eth", 0)
            if eth_balance > 0:
                return {
                    "action": "swap",
                    "token_in": "ETH",
                    "token_out": "TOKEN",
                    "amount_in": eth_balance * 0.1,
                    "max_slippage": self.max_slippage,
                    "reason": f"Pool undervalued by {abs(divergence):.2%}"
                }

        # If pool is overvalued beyond threshold -> Sell/Swap back
        elif divergence > self.mispricing_threshold:
            token_balance = balances.get("token", 0)
            if token_balance > 0:
                return {
                    "action": "swap",
                    "token_in": "TOKEN",
                    "token_out": "ETH",
                    "amount_in": token_balance * 0.5,
                    "max_slippage": self.max_slippage,
                    "reason": f"Pool overvalued by {divergence:.2%}"
                }

        return None

def decide(view):
    strategy = CustomStrategy()
    return strategy.decide(view)
