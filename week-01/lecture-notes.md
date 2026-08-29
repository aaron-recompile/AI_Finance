# Week 1 — On-Chain Foundations

## Lecture Notes

> **How this course works (say this on Day 1):** No PowerPoint. All notes are AI-generated Markdown, published to GitHub/Drive. We don't *study* the chain — we *build* on it. Every concept climbs the same **five-rung ladder**: (R1) see it → (R2) use it in a wallet → (R3) call it with code → (R4) build your own → (R5) hand it to your agent. Where you stop on the ladder is your track. Everything runs on **testnet — no real money, ever.**

### Learning Objectives

By the end of Week 1, students will be able to:

- Explain **why a machine economy needs a blockchain** (machines can't take each other to court, so the rules must be self-executing code).
- Explain that a blockchain is **one objective ledger**, and distinguish **Bitcoin (UTXO cash model) from Ethereum (account-balance + contract model)** and what each can compute.
- Explain, in plain language, what a **wallet, private key, transaction, gas,** and **smart contract** actually are — and demonstrate each on a live testnet.
- Set up the course toolchain: **GitHub, Claude Code, web3.py, MetaMask,** and a **testnet faucet.**
- Read live on-chain data with a few lines of code (R3).
- Explain what a **stablecoin** is and why it is the "base money" of on-chain finance.
- Explain the **AMM / `x*y=k`** model and perform a first **swap** (R2) and a **web3.py read** (R3).

### Session Structure

| Session | Length | Theme |
|---------|--------|-------|
| **Session 1** | 1.5 h | Demystification: keys, transactions, gas, contracts + environment |
| **Session 2** | 2 h | Financial Primitives I: stablecoins + Swap/AMM |

---

## Session 1 — Orientation & Demystification (1.5 Hours)

### The Big Picture: why this course exists

As AI shifts from *tool* to *autonomous economic actor*, agents will need to hold value, pay each other, and act **without a human in the loop**. The human banking system (KYC gates, business hours, intermediated settlement) is a poor fit for that. **Public blockchains are the native substrate for machine-to-machine finance:** programmable, permissionless, always on. This course teaches you to operate exactly there — and to build the agents that will live there.

**Why does it have to be a blockchain? Think about what happens when someone defaults.** Between people, a whole *institution* has our back: if you borrow and don't repay, I can take our contract to **court** — behind it stand police, enforcement, credit records. But what about two **AI agents** lending to each other? **No court hears a machine's lawsuit, no police show up, and an agent has no body to jail.** So who enforces the rules? Only the **code itself**: the terms of the loan aren't written on paper for a human to adjudicate — they're written as a **smart contract** that liquidates and seizes collateral automatically (you'll watch this happen in Week 2). **In a machine economy, "law" has to become "code," and the place that runs this code and everyone agrees on is the blockchain.** That is the fundamental reason this course exists.

> **Teaching tip:** Open with two questions: *"You lend a friend money and they don't pay you back — what can you do?"* (sue them, ding their credit) — *"Now two AIs lend to each other and one doesn't pay. Who steps in?"* Let them sit in it, then land it: *"Nobody — unless the rule itself is code that executes on its own. That's the blockchain, and that's this course."* Then add the micropayment gap: *"And if an AI wanted to pay another AI $0.001 right now, how would it do it with a credit card?"* (it can't — no account, no bank hours, no per-transaction card).

### Part 0: What a Blockchain Is — One Objective Ledger, Two Models

Before we install tools, let's be clear about *what we're actually dealing with*, or the rest is a black box.

**① A blockchain = one objective, public ledger that can only change by the rules.**
It's not a company's database (a company can quietly edit its own). It's a snapshot of state that **the whole network agrees on, anyone can read, and updates only by fixed rules**. "How much you have, what's locked in this contract" isn't "whatever some server says" — it's an **objective fact** anyone can independently verify. This is the bedrock for everything later: agents can do business without trusting each other precisely because the ledger is objective and the rules execute automatically.

**② Two main chains, two accounting models (get this difference and you understand half the field).**

| | **Bitcoin** | **Ethereum** |
|---|---|---|
| Mental model | **cash / checks** (UTXO) | **a bank account** (Account) |
| How money is tracked | as discrete "unspent outputs"; a tx spends old ones and mints new ones | each address has a **balance number**, added to / subtracted from |
| What it can compute | script is **deliberately limited**: multisig, timelocks, hashlocks — mainly "who's allowed to spend this" | **Turing-complete**: arbitrary logic, and an address can also carry **code (a contract)** |
| Best at | simple, rock-solid, ultra-auditable **store & transfer of value** | arbitrary **financial logic** — DeFi, lending, AMMs live here |

In one line: **Bitcoin makes "money" maximally simple and reliable; Ethereum ties "money + programmable rules" together.** This course builds "agents that execute financial strategy on their own," which needs **programmable rules** — so our main arena is **Ethereum-family (EVM) chains and their cheap Layer-2s**. (Bitcoin isn't "worse," it's a **different trade-off** — we revisit this in Week 6 on market structure.)

**③ A smart contract is just "that piece of code attached to an address."**
Because Ethereum is an account-plus-code model, you can write "loan terms" or "swap rules" as a program deployed at an address that anyone can call, that runs exactly as written, and that no one can alter mid-way. **"Law becomes code," in technical terms, is exactly this.** (More in Part 5.)

**④ web3.py = your hand reaching into this objective world.**
That "objective ledger" isn't abstract — a few lines of Python read it. Run `code/read_chain.py` in class (read-only, free, no login):

- connect to a **node** (RPC) → read the **latest block height** and **gas price**;
- read an address's **native ETH balance** (the node reads it straight from account state) — a live look at the **account model**;
- then read its **USDC token balance** (USDC is just a contract; the balance lives in the **contract's own ledger**, so you have to "ask the contract") — the most basic form of **interacting with a smart contract**.

> **Teaching tip:** After `read_chain.py`, land it: *"We installed no node, spent no money, signed into nothing — and we just read real on-chain data, because it's objective and public by design. You just touched that 'objective world' for the first time."* That turns the abstract word "blockchain" into something students physically touched — the ground R2/R3/R4 stand on.

### Part 1: Environment Setup (do this live, together)

> **Full step-by-step install manual:** `resources/setup-guide.md` — Python + venv, the pip libraries, Foundry, MetaMask + testnet, Claude Code, and a final verification checklist. Assign it as pre-work; walk the checklist in class.

We set up the exact toolchain we'll use all term. **If anything breaks, ask AI** — that's not cheating here, it's the method.

| Tool | What it's for |
|------|---------------|
| **GitHub** | Where your work lives and is submitted |
| **Claude Code** | Your AI pair — writes/debugs code with you (R3–R5) |
| **MetaMask** | A Web3 wallet — your hands-on window into the chain (R2) |
| **web3.py** | Python library to talk to the chain in code (R3) |
| **Testnet + faucet** | A free practice chain with valueless test coins |

**Do-now:** install MetaMask → switch to a testnet (e.g., Base Sepolia) → claim test coins from the faucet.

### Part 2: A Wallet Is Just a Keypair

A "wallet" is not a folder of coins. It is a **keypair**:

```
private key  ── (one-way math) ──▶  public key ── (hash) ──▶  address (0x02D3…)
```

- **Private key:** a giant secret number. *Whoever holds it controls the funds.* Never share it.
- **Address:** derived from the private key; safe to share — it's how people pay you.

**Analogy:** the address is your mailbox (public, everyone can drop mail in); the private key is the only key that opens it. Losing the key = losing the mailbox forever. There is no "forgot password."

> **Teaching tip:** Have everyone generate a keypair and paste only their **address** in the chat. Then say: *"Notice nobody could paste their private key even if they wanted to look cool — because you all instinctively know what it protects."*

### Part 3: A Transaction Is a Signed Message

To *do* anything on-chain, you send a **transaction** — a message signed by your private key.

```
{ from, to, value, data, nonce }  + your signature (r, s, v)
```

- The network **recovers your address from the signature** — proving it's you — without you revealing the key.
- The **nonce** (a counter) stops the same signed message from being replayed twice.

**This "sign an intent, the network verifies and executes" pattern is the spine of everything** — it's the same shape as an agent placing a trade or authorizing a payment (we'll see it again in Weeks 5–6).

### Part 4: Gas — Paying for Computation

Every transaction consumes **gas** — a fee that pays the network to run your computation and store the result. No gas, no execution.

- Gas is why you can't spam the chain for free.
- On cheap Layer-2s (Base, Arbitrum) gas is a fraction of a cent; on Ethereum L1 it can be dollars. **This price difference is why the whole "agent micropayment" economy lives on L2s** (Week 5).

> **R1 live demo (strongly recommended, open it in class):** <https://txcity.io/v/eth-btc>
> An animation that turns the blockchain into a **bus system**: **the people queuing = pending transactions, each arriving bus = a block, boarding = getting included, the fare (Gwei / Sat/vB) = the fee.** The two streets are **Ethereum vs. Bitcoin** — a free live view of Part 0's "two models, two fee units." Let students watch for a minute: in low demand it's "empty 0-Gwei buses," in congestion the waiting room is packed. **Plant this detail now — "the higher-fare person boards first" — Week 4's MEV grows straight out of it.**

### Hands-On: The Four Basic web3.py Operations (R3 code + R2 UI)

Every later week reuses these four operations. Do them once now and students carry a "universal feel" forward. **Three scripts, all runnable on a local anvil in class.**

**① Read a balance + read a contract** (`code/read_chain.py`, already run in Part 0): connect a node, read block/gas; read an address's **native ETH balance** (ask the node) and its **USDC token balance** (ask the contract, one view call). Reading **changes nothing and costs nothing**.

**② Send a native asset** (`code/send_asset.py`): actually move ETH. Local demo, account0 sends 1 ETH to account1:
```
before: me 10000 ETH | them 10000 ETH
broadcast tx hash … → mined in block, status success
after:  me 9998.999958 ETH (−1.00004 incl. gas) | them 10001 ETH (+1)
```
You see a transaction's full life cycle: **assemble → sign with the private key → broadcast → wait to be mined.**

**③ Interact with a contract: read (view) + write (state-changing) + send a token asset** (`code/interact_contract.py`):
a token isn't the chain's native asset — it's **just a balance table inside a contract**; sending a token isn't "a plain transaction," it's **"calling the contract's `transfer` function."** Demo: deploy a DEMO token → `balanceOf` (read, free) → `transfer 250` (write, a tx) → read again:
```
② read: me 1,000 DEMO | them 0
③ write: transfer 250 → mined, success
   read again: me 750 DEMO | them 250
```
**This nails "call vs. send / view vs. state-changing"** — used every week after (Week 2's AMM: reading the price = call, swapping = send, exactly this).

**④ R2 UI cross-check** (MetaMask): click **Send** to move test ETH, and look at token balances under Assets. **Code and UI are two doors to the same thing** — the UI just runs the steps above.

> **Pivot question (throws us straight into Session 2):** you can now **hold, transfer, and even call a contract to move assets** — **but "transfer" is not "trade."** To swap ETH for USDC, **who trades with you? Nobody is waiting on the other side.** That gap is exactly what next session's **AMM** fills.

### Part 5: Smart Contracts — Code That Lives On-Chain

A **smart contract** is a program deployed to an address. Anyone can call its functions by sending a transaction. It runs exactly as written, publicly, with no operator to trust.

- A token (USDC), an exchange (Uniswap), a lending market — all just contracts.
- **Composability:** any contract can call any other. This is DeFi's superpower *and* its biggest attack surface (Weeks 3 & 6).

> **Teaching tip:** Reframe: *"A smart contract is a vending machine made of math. You put in the right input, you get the guaranteed output, and nobody — not even the owner — can reach in and change the result mid-transaction."*

### Part 6: The Five-Rung Ladder (our method for the whole term)

| Rung | You… | Track |
|------|------|-------|
| R1 Illustrate | see *what it is* | everyone |
| R2 Use | operate it in MetaMask | everyone |
| R3 Interact | call it with web3.py (via Claude Code) | main / advanced |
| R4 Build | write & deploy your own toy contract | advanced |
| R5 Delegate | hand the capability to your own agent | advanced |

**Every topic ends at the same question: *can the agent do this by itself?***

### R5 Preview + This Week's Homework: Hand the Operations to an Agent

In class you ran three things **by hand** (read / send / interact). The **homework** is to wrap them as **agent tools, add a guardrail, and let an agent do them itself** — reaching R5. We teach the local code in class and leave agent-ification for students to climb on their own:

- `code/agent_tools.py`: wraps the three operations as "tool functions," each **write** operation gated by a **Guard (per-call cap + whitelist)**. `python3.11 agent_tools.py` shows: when the agent asks to send 5 ETH, or to pay a stranger, it's **blocked by the guard off-chain — no transaction ever goes out.**
- `code/openclaw-agent.template.jsonc`: a template for wiring these tools into **OpenClaw** (students fill it in from the official docs).
- **Tiered grading** (see `lab-exercise.md`): running `agent_tools.py` by hand with a screenshot earns credit; **a working OpenClaw agent screenshot earns an A+.** Hard deadline, but late turn-in is accepted.

> This plants the idea of a "guardrail": **give an AI a private key, and you must give it a guardrail at the same time.** Week 5 opens this up into full "coordinator / signer separation."

### Part 7: This Session Is the Map of the Whole Course (each week answers a question Week 1 raises)

Today you managed to "hold + transfer an asset." Follow that one thing forward, and every later week is its natural extension — so students know from day one where they're headed and why:

| From which gap in Week 1 | Leads to |
|--------------------------|----------|
| You can transfer, but **nobody trades with you** | **Week 2: AMM** — swapping with no counterparty |
| Liquidity is deep, and you want **limit orders / leverage** | **Week 6: central-limit order books (CLOB) + perpetuals & derivatives** (Hyperliquid) |
| You want to **use money without selling your coins** | **Week 3: lending & liquidation** |
| Your tx must **queue in a public waiting room**, and order decides who profits | **Week 4: MEV** — order = money, tied to chain mechanics & the **mempool**; traditional **HFT** plays the same "who's first" game |
| **Hand any of the above to an agent** that signs and executes on its own | **Weeks 5 & 7: agent-ification and integration** |

> **In one line: Week 1 teaches you to *touch* this objective world (read + send one); every week after teaches you to *do* something more complex on it; and finally, to hand it to an agent.**

---

## Session 2 — Financial Primitives I: Stablecoins & Swap/AMM (2 Hours)

### Part 1: Stablecoins — the Base Money of On-Chain Finance

A **stablecoin** (e.g., USDC) is a token pegged to $1. It's the unit everyone prices in, because raw crypto is too volatile to quote a coffee in.

- On-chain, USDC is *just a smart contract* tracking balances.
- It supports **gasless transfer authorizations** (EIP-3009) — you *sign* a transfer and someone else submits it. **Hold onto this; it's the engine of the x402 payment agent in Week 5.**

### Part 2: Swap and the AMM (`x * y = k`)

How do you trade token A for token B with no order book and no counterparty waiting? An **Automated Market Maker**: a contract holding a pool of both tokens, pricing by a formula.

```
x * y = k        (x = reserve of A, y = reserve of B, k = constant)
```

- You add A, you remove B, such that the product **k stays constant**. The bigger your trade relative to the pool, the worse your price — that's **slippage**.
- **Impermanent loss** (a sub-concept, not a headline) is what a liquidity provider "loses" versus just holding, when prices move.

**Analogy:** a see-saw that must keep its *area* constant. Push one side down (add A), the other rises (B gets scarcer, pricier). Small pushes barely move it; huge pushes swing it hard (slippage).

> **Teaching tip:** Draw the hyperbola `x*y=k` once. Mark a small trade (tiny price move) vs. a huge trade (big move along the curve). Slippage becomes *visual*, not a formula to memorize.

### Part 3: Hands-On (R1 → R2 → R3)

1. **R1 — Illustrate:** we just did — keypair, tx, gas, contract, AMM.
2. **R2 — Use:** in MetaMask on testnet, perform one **swap** (stablecoin ↔ test token). Watch the amount-out, the slippage, and the gas.
3. **R3 — Interact:** with Claude Code, write ~10 lines of **web3.py** to read the pool's reserves and print the current price. *You just read the chain with code.*

> **Preview of Week 2:** next week we don't just *use* an AMM — you **build your own Uniswap** (the `x*y=k` toy contract) and swap on it. Rung R4.

---

### Key Takeaways

- A **wallet = keypair**; the **private key is everything**; the address is public.
- A **transaction = a signed intent**; the network verifies by **recovering your address from the signature**. (Remember this shape.)
- **Gas** pays for computation; cheap **L2s** are what make micro-scale agent finance possible.
- A **smart contract** is public, unstoppable code at an address; **composability** is the superpower and the risk.
- **Stablecoins** are the base money; **AMMs** (`x*y=k`) let anyone swap, at the cost of **slippage**.

### Vocabulary

| Term | One-line meaning |
|------|------------------|
| Private key | Secret number that controls the wallet |
| Address | Public identifier derived from the key |
| Transaction | A signed message that changes on-chain state |
| Nonce | Counter that prevents replaying a transaction |
| Gas | Fee paid to run/store a transaction |
| Smart contract | A program deployed at an on-chain address |
| Composability | Contracts freely calling other contracts |
| Testnet | A free practice chain with valueless coins |
| Stablecoin | Token pegged to $1 (e.g., USDC) |
| AMM | Automated Market Maker; prices swaps by `x*y=k` |
| Slippage | Worse price you get for a larger trade |
| Impermanent loss | LP's loss vs. holding when prices move |

### Instructor Prep Checklist (for me, not students)

- [ ] Testnet faucet actually dispensing before class (have a backup faucet).
- [ ] A known-good testnet AMM pool for the Session 2 swap (pre-verify it isn't empty).
- [ ] `web3.py` read snippet tested against the pool the morning of class.
- [ ] One spare funded testnet wallet to bail out a stuck student.
