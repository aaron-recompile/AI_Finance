# Command Concepts — AI Finance Course

## Start here
**Don't memorize syntax. Learn to *vibe*.**
The real skill this course builds is: **say what you want in plain words, and let AI (or the ready scripts in `code/`) produce the exact command.** Know *what is possible* (the concept); the syntax you can always ask for. You only truly need to remember a handful of commands — the rest is a conversation.

> The moment you can name the operation ("I want to *read* my balance", "I want to *change* on-chain state"), you can drive any tool — a shell, `web3.py`, `cast`, or an AI agent.

## The few you should actually know
```shell
cd <folder>                       # go somewhere
ls                                # what's here?  (Windows: dir)
source ai_finance/bin/activate    # enter the course env  (Windows: ai_finance\Scripts\activate)
git pull                          # get the latest course code
python <script>.py                # run a course tool
```
Everything below is a *concept* with the commands that serve it. **Read = free. Write = a signed transaction that costs gas.** That one line is the spine of the whole course.

---

## 1. LOCATE & ENTER — "Am I in the right place, with the right tools?"

### Commands
```shell
cd "…/AI Finance/course"          # be in the project
source ai_finance/bin/activate    # prompt should show (ai_finance)
git pull                          # newest scripts (or: git clone <repo> the first time)
cd weeks/week-01/code             # where the tools live
```

### Vibe
* "Put me in the course folder with the environment active."
* "Get me the latest code the instructor pushed."
* "Am I using the right Python? (it should say `(ai_finance)`)"

**Why:** 90% of "it doesn't work" is *wrong folder* or *env not active*. Locate first, act second.

---

## 2. READ — "What exists? What's the chain saying?"  *(free, changes nothing)*

### Commands
```shell
python read_chain.py                          # block, gas, an address's ETH+USDC (real chain)
ADDR=0xYou python check_balance.py            # my ETH + USDC on Base Sepolia
cast call $TOKEN "balanceOf(address)" $ME     # ask a contract a question
ls ; cat SETUP.md                             # what files exist / read one
```

### Vibe
* "How much USDC does this address hold right now?"
* "What's the current block and gas price?"
* "Ask the token contract for my balance — don't change anything."

**Why:** Reading is **free and safe** (`eth_call` / `.call()`). Always *look* before you *touch*. In web3, a read never costs gas and never moves anything.

---

## 3. CREATE / ISSUE — "Bring into existence what isn't there yet."

### Commands
```shell
python gen_wallet.py                                                  # a new keypair (address + private key)
NAME="Aaron Coin" SYMBOL=AARON SUPPLY=888888 python issue_asset_basesepolia.py   # deploy a token on Base Sepolia
mkdir week-2-notes                                                    # a new folder
forge init my-defi                                                    # a new Solidity project
```

### Vibe
* "Make me a fresh wallet — give me the address, keep the key secret."
* "Issue a token called AARON with a supply of 888,888."
* "Scaffold a new Foundry project."

**Why:** "Issuing an asset" = **deploy a contract + mint**. Creation is just another action — the leverage (and the responsibility) is that it's now one command.

---

## 4. TRANSACT / WRITE — "Move value. Change on-chain state." *(signed, costs gas)*

### Commands
```shell
PRIVATE_KEY=0xYou TO=0xThem AMOUNT_ETH=0.0002 python send_asset.py    # send native ETH
TOKEN=0xTok TO=0xThem AMOUNT=250 python transfer_token.py            # send a token (a contract call)
cast send $AMM "swap0For1(uint256)" 5e18 --private-key $PRIVATE_KEY   # a swap, later
```

### Vibe
* "Send 0.0002 ETH to my classmate."
* "Transfer 250 of my token to this address."
* "Sign this intent and broadcast it; tell me when it's mined."

**Why:** Every write is the same shape — **build → sign → send → wait for receipt.** It costs gas, needs your key, and changes the ledger. *Sign an intent; the network verifies and executes.*

---

## 5. BUILD & VERIFY — "Compile it, test it, prove it works before trusting it."

### Commands
```shell
anvil                                 # a local throwaway chain (instant, free)
forge build                           # compile Solidity → bytecode + ABI
forge test -vv                        # run the tests (green = the properties hold)
forge script script/Deploy.s.sol --broadcast   # deploy
```

### Vibe
* "Compile my contract and show me any errors."
* "Run all tests and confirm the edge cases pass."
* "Spin up a local chain so I can try this for free before touching a testnet."

**Why:** Unverified code is a liability. A test is you writing down *the property that must always hold* — and letting the machine check it (Session on Foundry goes deep here).

---

## The one habit that unlocks everything: **variables, not hardcoding**

Anything that changes — the node, the address, your key, the token — is passed as a **variable**, so the *same tool* points anywhere without editing code:
```shell
RPC=<node>  ADDR=<address>  PRIVATE_KEY=<key>  TOKEN=<contract>   python <script>.py
```
```shell
export RPC=https://base-sepolia-rpc.publicnode.com   # set once per terminal, then commands stay short
ADDR=0xOther python check_balance.py                 # override just what changes, right now
```

### Vibe
* "Run the same balance check, but against Ethereum mainnet this time."
* "Use my key for this one, don't change the default."

**Why:** Never bake the changeable into the code. **Default the common case; override the temporary one.** This is why one `transfer_token.py` can move *any* ERC-20 — even USDC — just by changing `TOKEN=`.

---

## How to actually work like this
1. Say the **intent** in plain words ("I want to check my USDC balance").
2. Name the **operation** (that's a READ).
3. Reach for the matching command — or **ask AI for the exact syntax**. Asking AI *is* the method in this course, not cheating.
4. For anything that **writes**, pause: right key? right address? testnet? *(A read is safe; a write is a real transaction.)*
