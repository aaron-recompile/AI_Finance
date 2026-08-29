# Week 1 Lab (Homework): Touch the Chain, Then Hand It to an Agent

**Weight:** counts toward weekly Labs. **Due:** before Week 2, Session 3. **Late turn-in accepted** (marked late) — don't skip it.
**Prerequisite:** finish [`SETUP.md`](../SETUP.md) (conda env + `web3` + cloned repo). Every terminal: `conda activate ai_finance` first — your prompt must show `(ai_finance)`.
**Note:** run scripts with plain `python` inside the `ai_finance` env. Write-state scripts run on **Base Sepolia testnet** using the test ETH you got in class (no local node needed). 🪟 Windows: set variables with `set VAR=value` on their own line (no space after `=`).

## Goal

First *touch* this objective world by hand (read + send), then **wrap those operations as tools, add a guardrail, and hand them to an agent** — walking the full R1→R5 arc of Week 1.

## Track A — Main (everyone)

1. **Environment proof.** Paste into `reflection.md`:
   ```bash
   python --version
   python -c "import web3, eth_account; print('web3', web3.__version__)"
   ```
   Plus the output of `check_balance.py` on **your** funded testnet address, showing your test ETH:
   ```bash
   # 🍎 macOS/Linux
   ADDR=0xYourAddress python check_balance.py
   # 🪟 Windows: set ADDR=0xYourAddress   then   python check_balance.py
   ```
2. **Read the chain.** Run `code/read_chain.py`, paste the output. One sentence: *what did you read, and why did it cost nothing and need no login?*
3. **Send a native asset to a classmate.** On Base Sepolia, send a small amount with your own key:
   ```bash
   RPC=https://base-sepolia-rpc.publicnode.com PRIVATE_KEY=0xYOURkey TO=0xCLASSMATE AMOUNT_ETH=0.0002 python send_asset.py
   ```
   Paste the before/after balances and the tx hash. One sentence: *from pressing enter to the asset arriving, what steps did the transaction go through?*
4. **(Optional — preview of Week 2) Interact with a contract (read + write).** `code/interact_contract.py` deploys a demo token, then does `balanceOf` (read) and `transfer` (write). It needs a local `anvil` node — that's **Foundry, which we install in Week 2** — so this step is optional now. If you already have `anvil`, run it and answer: *what's the essential difference between `balanceOf` (read) and `transfer` (write) — why is one free and the other a transaction?*

## Track B — R5: Hand the operations to an agent (everyone does 5; 6 goes for A+)

5. **Tools + guardrail (run it yourself).** Run `code/agent_tools.py` (point it at Base Sepolia with `RPC` + your `PRIVATE_KEY`, or its built-in local default). Paste the output. Answer: *the two blocked calls (over-cap, and paying a stranger) — what stopped them, and why did "no transaction ever go out"?* Then lower the guard's `eth_cap` so a call that used to pass now gets blocked; paste before/after.
   > **This tier already earns solid credit** — you showed "tools + guardrail" work and can explain them.
6. **Wire up your own agent (for the A+).** Using `code/openclaw-agent.template.jsonc`, connect these tools to **OpenClaw** (check the official docs, turn the template into a real config). Give the agent one natural-language instruction (e.g., "check FRIEND's balance, then send it a little ETH") and let it **call the tools and complete it within the guardrail**. **Paste a screenshot of the agent running** (instruction + tool calls + result).
   > **A working OpenClaw agent screenshot = A+.** If you can't get there, the Step-5 hand-run screenshot still earns credit.

## Deliverables (push to your repo)

- Your modified `read_chain.py` / `agent_tools.py` (your guard change)
- `reflection.md` (all Track A answers + the `check_balance.py` proof; Track B: `agent_tools` output + guard before/after; for A+, the OpenClaw screenshot)

## Grading (12 pts)

| Criterion | Pts |
|-----------|-----|
| Environment proof complete (versions + `check_balance.py` shows your test ETH) | 3 |
| Read + send to a classmate both run, questions answered correctly | 4 |
| `agent_tools.py` runs + "guard blocks off-chain" explained correctly | 3 |
| Lower the guard → reproduce a block | 2 |
| **Track B step 6: working OpenClaw agent screenshot** | **+2 (caps at A+)** |

> **Tier note (important):**
> - **Hand-run `agent_tools.py` + screenshot** → main credit (pass to good).
> - **A real OpenClaw agent running + screenshot** → **A+.**
> Both paths count; getting stuck on an agent framework the first time is normal — **don't skip submitting just because OpenClaw won't connect;** the hand-run tier still earns credit.

## Prompts you can use

- *"Explain what a JSON-RPC endpoint is, like I've never used one."*
- *"Following openclaw-agent.template.jsonc, help me check the OpenClaw docs and turn it into a config that actually loads."*

> **Honesty note:** the point of Week 1 is to remove the mystery. If any step felt like magic, ask AI to explain it until it doesn't — then write that understanding in `reflection.md`.
