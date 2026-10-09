#!/usr/bin/env python3
"""A tiny runnable scenario on the minimal prediction market. Run: python3 demo.py"""
from prediction_market import Market

m = Market("Will a certain AI unicorn IPO before year end?", prob=0.50)
print("Q:", m.question)
print(f"YES price starts at {m.yes_price():.2f}  = the market says 50% chance\n")

m.buy("alice", "YES", 10)        # Alice bets it happens
m.buy("bob", "NO", 10)           # Bob bets it does not
print(f"after Alice buys YES and Bob buys NO -> YES price {m.yes_price():.2f}")

for _ in range(5):               # a rumor spreads; the crowd piles into YES
    m.buy("crowd", "YES", 5)
print(f"after good news, the crowd buys YES -> YES price {m.yes_price():.2f} (= ~{m.yes_price()*100:.0f}% probability)\n")

payouts = m.resolve("YES")       # the optimistic oracle declares the result
print("the oracle declares: YES. every YES share pays $1, every NO share pays $0.\n")
for who in ("alice", "bob"):
    print(f"  {who:6} spent ${m.spent.get(who,0):.2f}  ->  paid ${payouts.get(who,0):.2f}  |  pnl ${m.pnl(who, payouts):+.2f}")

print("\nAlice (YES) won; Bob (NO) lost his stake. The price was the probability all along.")
