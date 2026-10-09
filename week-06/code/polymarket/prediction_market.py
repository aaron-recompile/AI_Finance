"""A minimal YES/NO prediction market -- teaching skeleton.

One idea: a share pays $1 if its side wins and $0 if it loses.
  - YES share: pays $1 if the event happens, else $0
  - NO share : pays $1 if it does NOT happen, else $0
So YES price + NO price = $1, always. And the YES price (0..1) IS the market's
probability that YES happens.

This is the third app of "one engine, three apps": spot / perp / prediction.
A prediction market is like a perpetual that settles exactly once, to 0 or 1.

Deliberately tiny: no order book, no real collateral, no chain -- just the concepts.
Stdlib only.
"""


class Market:
    def __init__(self, question, prob=0.5):
        self.question = question
        self.prob = prob            # the market's belief that YES happens (= the YES price)
        self.resolved = None
        self.positions = {}         # name -> net YES shares (negative = NO shares)
        self.spent = {}             # name -> cash spent so far

    def yes_price(self):
        return self.prob

    def no_price(self):
        return 1 - self.prob

    def buy(self, name, side, shares, impact=0.02):
        """Buy `shares` of YES or NO at the current price. The trade nudges the probability
        toward that side (more demand for YES -> YES gets more likely)."""
        if self.resolved:
            raise ValueError("market already resolved")
        price = self.yes_price() if side == "YES" else self.no_price()
        cost = shares * price
        signed = shares if side == "YES" else -shares
        self.positions[name] = self.positions.get(name, 0) + signed
        self.spent[name] = self.spent.get(name, 0.0) + cost
        self.prob = min(0.99, max(0.01, self.prob + impact * (1 if side == "YES" else -1)))
        return cost

    def resolve(self, outcome):
        """The optimistic oracle declares the result: 'YES' or 'NO'.
        Each winning share pays $1; losing shares pay $0. Returns {name: payout}."""
        if outcome not in ("YES", "NO"):
            raise ValueError("outcome must be 'YES' or 'NO'")
        self.resolved = outcome
        payouts = {}
        for name, y in self.positions.items():
            won = y if outcome == "YES" else -y     # YES shares win on YES, NO shares win on NO
            payouts[name] = max(won, 0) * 1.0
        return payouts

    def pnl(self, name, payouts):
        """Final profit = what you were paid out minus what you spent."""
        return payouts.get(name, 0.0) - self.spent.get(name, 0.0)
