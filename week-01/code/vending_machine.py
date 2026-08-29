"""
Week 1 - Part 5: a smart contract is a vending machine made of math
Feel the essence in ~30 lines: right input -> guaranteed output, and NOBODY -- not even the
owner -- can reach in and change the result of your purchase. We contrast two "shops":
  - VendingMachine (a smart contract): one fixed rule in code, deterministic, no owner hook.
  - ShadyShop (a normal server / human operator): can take your money and change its mind.

run:  python vending_machine.py
"""


class VendingMachine:
    """A vending machine made of math. The rule below is the WHOLE behavior -- public, fixed,
    and there is no secret branch 'for the owner'. Put in enough, you always get the item + change."""
    PRICE = 3  # fixed and public

    def buy(self, coins: int) -> dict:
        if coins < self.PRICE:
            return {"item": None, "refund": coins, "note": "not enough -> coins returned, always"}
        return {"item": "SNACK", "change": coins - self.PRICE}


class ShadyShop:
    """A normal server: a human operator decides. They can take your money and simply... not deliver."""
    PRICE = 3

    def __init__(self):
        self.owner_will_honor = True   # the owner's mood -- an off-chain switch they control

    def buy(self, coins: int) -> dict:
        if coins < self.PRICE:
            return {"item": None, "refund": coins}
        if not self.owner_will_honor:                 # the operator reaches in
            return {"item": None, "kept_your_money": coins, "note": "owner changed their mind (rug)"}
        return {"item": "SNACK", "change": coins - self.PRICE}


def demo():
    print("=" * 60)
    print("(1) The smart contract (vending machine made of math)")
    vm = VendingMachine()
    print("   buy(5):", vm.buy(5))
    print("   buy(2):", vm.buy(2))
    print("   buy(5) three times ->", [vm.buy(5) for _ in range(3)])
    print("   deterministic: same input, same output, every time.")

    print("\n(2) Can the OWNER cheat this purchase? Look for a hook...")
    print("   VendingMachine.buy has NO branch that depends on an owner. There is nothing to flip.")
    print("   The only 'power' an owner has is to deploy a DIFFERENT machine later --")
    print("   they cannot change the result of a purchase already running. That is 'no operator to trust'.")

    print("\n(3) Contrast: a normal server where a human decides (ShadyShop)")
    shop = ShadyShop()
    print("   you pay 5, owner honest :", shop.buy(5))
    shop.owner_will_honor = False                     # the operator flips a switch after taking money
    print("   you pay 5, owner flips  :", shop.buy(5))
    print("   -> the operator kept your money. You had to TRUST them, and trust can be betrayed.")

    print("\nTakeaways:")
    print("  - A smart contract = a vending machine made of math: right input -> guaranteed output.")
    print("  - It runs EXACTLY as written, in public; no owner can reach in mid-purchase and change it.")
    print("  - A token, an exchange, a lending market are all just such machines.")
    print("  - And machines can call other machines -> composability (the superpower, and the attack surface).")
    print("=" * 60)


if __name__ == "__main__":
    demo()
