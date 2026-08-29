# Week 1 · Foundations & Reference Pack

> **How to use this (separate from the lecture notes):**
> The lecture notes teach the "just enough" layer; this pack is for **shoring up your foundations**.
> 1. Read each **30-second compressed version** — if it's clear, skip ahead.
> 2. If a point feels shaky, follow its **deeper references** (books/docs/videos — **read as much as you want, no cap**).
> 3. Stuck on anything — **just ask AI.** In this course that's the method, not cheating.
>
> **Layout convention:** each point = `Compressed` → `Why we need it this week` → `Deeper refs (tiered)` → `Self-check` → `Ask AI`.
> Legend: 📘 book · 📄 free doc/whitepaper · 🎥 video · ⭐ read this first.

---

## A. Pre-course foundations (fill only the gaps you have)

> These are things the course "assumes you already know." **Self-check: whichever you're unsure of, go shore up.**

### A1. Command line / Terminal
- **Compressed:** the terminal is a window where you type commands to control the computer. You need 5: `cd`, `ls`, `mkdir`, `python x.py`, `git ...`.
- **Why:** the whole course runs scripts and sends transactions from the terminal.
- **Deeper:** ⭐📄 MDN "Command line crash course" (20 min); your CSE/MB600 Python Week 1 terminal material.
- **Self-check:** can you blind-type "make a folder and enter it"? (`mkdir demo && cd demo`)
- **Ask AI:** *"Explain the 5 most essential terminal commands with one example each, like I've never used a terminal."*

### A2. Git / GitHub
- **Compressed:** Git snapshots your code over time; GitHub stores snapshots in the cloud and is where you submit work. Core: `add → commit → push`, plus `clone`.
- **Why:** all labs, notes, and code live on GitHub.
- **Deeper:** ⭐📘 Pro Git (free) — chapters 1–2; 🎥 "Git in 15 minutes".
- **Self-check:** can you push a change to your own repo?
- **Ask AI:** *"Walk me through committing and pushing my first change to a new GitHub repo, step by step on macOS."*

### A3. Python refresher
- **Compressed:** variables, functions, `dict`/`list`, `import`, `pip install` — enough to start; ask AI for the rest.
- **Why:** from R3 on we call the chain with web3.py (Python).
- **Deeper:** ⭐📄 Official Python tutorial (ch. 3–5); 📘 *Starting Out with Python* (Gaddis).
- **Self-check:** can you read `for k, v in d.items(): print(k, v)`?
- **Ask AI:** *"Give me a 10-line Python cheat sheet covering dicts, lists, functions, and imports."*

### A4. What HTTP / an API is
- **Compressed:** a client sends a **request** (GET to fetch / POST to create); a server sends a **response** (status 200 ok / 404 not found / 402 payment required) + data.
- **Why:** Week-5 x402 payments and all chain reads are HTTP underneath.
- **Deeper:** ⭐📄 MDN "HTTP overview".
- **Self-check:** roughly what does `402 Payment Required` mean? (You'll hit it in Week 5.)
- **Ask AI:** *"Explain HTTP requests, responses, and status codes with a restaurant analogy."*

### A5. Basic finance vocabulary
- **Compressed:** **spot** = immediate price for delivery now; **derivative** = a contract whose price tracks something else; **liquidity** = how much you can trade without moving price; **order book** = the list of buy/sell orders.
- **Why:** Weeks 2 & 6 assume these when covering AMMs, perps, order books.
- **Deeper:** 📄 Investopedia entries (Spot/Derivative/Liquidity/Order Book); 📘 *DeFi and the Future of Finance* (Harvey) ch. 1.
- **Self-check:** which is a derivative — spot or a perpetual future?
- **Ask AI:** *"Define spot, derivative, liquidity, and order book, each in one sentence a beginner understands."*

---

## B. Week 1 core concepts (per point: compressed + deeper)

### B1. Wallet & keys
- **Compressed:** a wallet is a **keypair**, not a folder of coins. The **private key is a huge secret number; whoever holds it controls the funds.** The address is derived one-way and is public. Lose the key = lost forever; no "reset password."
- **Why:** every later step (signing, ordering, an agent holding funds) starts with "who holds the key."
- **Deeper:** ⭐📘 Mastering Ethereum (free, GitHub) — **ch. 4 Keys & Addresses**; 📄 your own *Mastering Taproot* (deeper, Bitcoin side).
- **Self-check:** why can the address be public but not the private key?
- **Ask AI:** *"Explain public vs. private keys with an analogy, and why sharing the address is safe."*

### B2. Transaction & signature
- **Compressed:** to change on-chain state you send a **transaction** — a message **signed** by your private key: `{from,to,value,data,nonce} + signature (r,s,v)`. The network **recovers your address from the signature** to verify it's you, without you revealing the key; `nonce` prevents replay.
- **Why:** this "sign an intent → someone verifies → executes" shape is the same backbone as x402 payments and agent orders.
- **Deeper:** ⭐📘 Mastering Ethereum **ch. 6 Transactions**; 📄 EIP-712 / EIP-3009 specs (for Week-5 off-chain signed authorizations).
- **Self-check:** if you change the amount in a transaction but don't re-sign, what happens?
- **Ask AI:** *"Explain how a blockchain verifies who sent a transaction without seeing the private key."*

### B3. Gas
- **Compressed:** every transaction burns **gas** — a fee that pays the network to run + store it. No gas, no execution. Cents on an L2 (Base); dollars on L1.
- **Why:** "agent micropayments only work on cheap L2s" traces back to gas.
- **Deeper:** 📘 Mastering Ethereum **ch. 6 (gas)**; 📄 ethereum.org "Gas and fees".
- **Self-check:** why is the same action far cheaper on Base than on Ethereum L1?
- **Ask AI:** *"Explain gas fees and why Layer-2 chains are so much cheaper than Ethereum mainnet."*

### B4. Smart contract & EVM
- **Compressed:** a smart contract is a program at an address; anyone can call it; it runs exactly as written, publicly, with no operator to trust. **Composability** = contracts calling contracts (superpower + attack surface). The EVM is the "virtual machine" that runs them.
- **Why:** tokens, AMMs, lending, and the Uniswap you'll build are all contracts.
- **Deeper:** ⭐📘 Mastering Ethereum **ch. 7 Smart Contracts & Solidity**, **ch. 13 EVM**; 📄 Uniswap v2 Whitepaper (skim before Week 2).
- **Self-check:** why does "no one can change the result mid-transaction" matter for finance?
- **Ask AI:** *"Explain smart contracts and composability with a vending-machine analogy."*

### B5. Testnet & faucet
- **Compressed:** a testnet is a practice chain where **coins are worthless** (e.g., Base Sepolia); a faucet dispenses free test coins. The whole course runs here — no real money.
- **Why:** to master every experiment safely.
- **Deeper:** 📄 the official faucet page for our testnet (I'll confirm it dispenses before class).
- **Self-check:** can testnet coins be exchanged for real money?
- **Ask AI:** *"What is a blockchain testnet and how do I get free test coins from a faucet?"*

### B6. Stablecoin
- **Compressed:** a token pegged to $1 (USDC), the base unit of on-chain finance; underneath it's just a contract tracking balances. Supports **EIP-3009 gasless transfer authorization** (you sign; someone else submits).
- **Why:** that EIP-3009 property is the engine of the Week-5 x402 payment agent.
- **Deeper:** 📄 Circle USDC developer docs (EIP-3009); 📘 Mastering Ethereum **ch. 10 Tokens**.
- **Self-check:** how is USDC fundamentally different from "dollars in a bank"?
- **Ask AI:** *"Explain what a stablecoin is and how EIP-3009 'transfer with authorization' works."*

### B7. AMM / `x*y=k` / slippage
- **Compressed:** you can swap with no order book — an **AMM** prices via `x*y=k`. The larger your trade vs. the pool, the worse the price = **slippage**; **impermanent loss** is an LP's paper loss vs. holding (a sub-concept, not a headline).
- **Why:** next week you build a `x*y=k` toy Uniswap yourself.
- **Deeper:** ⭐📄 Uniswap v2 Whitepaper; 📘 *DeFi and the Future of Finance* (AMM/DEX chapters); 🎥 "How Uniswap works" (any 10-min explainer).
- **Self-check:** why does a big trade move the price sharply in a small pool?
- **Ask AI:** *"Derive the AMM swap output from x*y=k and explain why slippage grows with trade size."*

---

## Note (for the instructor, not the student version)

- **Two layers:** A = pre-course catch-up (only if a gap); B = this week's new concepts (everyone).
- **Each point = four parts:** compressed / why this week / tiered deeper refs (no cap) / one self-check — plus an **Ask AI** prompt (added per the pending question in the ZH pack).
- Pairs with `lecture-notes.md`: the lecture teaches "just enough"; this pack handles "go deeper / catch up."
