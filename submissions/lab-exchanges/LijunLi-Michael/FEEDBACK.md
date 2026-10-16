# Three-exchanges lab — feedback

**Name:** Lijun Li
**GitHub:** LijunLi-Michael

## What I did
- Spot: Deposited 10 tUSDC, placed buy order #1274883 (0.05 MAX @ 186). Order did not fill — market moved above my limit price.
- Perp: Deposited 10 tUSDC margin, opened a long position (1 contract, 10x leverage, isolated). Position filled.
- Prediction: Deposited 10 tUSDC principal, bought YES ×10 shares at ~65 cents.

## Feedback (2–3 sentences)
The deposit flow confused me at first: after the on-chain deposit succeeded, my exchange balance still showed 0 until I logged out and back in. The "underlying network changed" warning on the perp and prediction pages was also confusing since my wallet was on the correct network (Base Sepolia, chain ID 84532). I'd add an explicit balance refresh button and a deposit confirmation state so users know the funds are on the way.

## (Bonus) Bug report
What I did: deposited 10 tUSDC from my wallet 0xd6577071c229c0e0B373E111fA7A862E844F7588 to the spot venue via Deposit → MetaMask confirm. What happened: the deposit tx 0xbda66b477afc08fcb0649dc122b9b1bffffebeceffbddb9501aaab58ee1de85a succeeded on-chain (block 48073597, 2026-10-13 18:18:02 UTC, 10 tUSDC arrived at custody wallet 0x6514F5a9b62b67d34f93841d9b84e2131fd973e8), but my exchange ledger balance stayed 0 for several minutes and my buy order could not fill. Refreshing the page (F5 / refresh button) did not update the balance; only logging out and back in made the 10 tUSDC appear. What I expected: the ledger to credit 10 tUSDC within a minute or two of the on-chain confirmation, without requiring re-login.

## Screenshots
spot.png · perp.png · prediction.png

