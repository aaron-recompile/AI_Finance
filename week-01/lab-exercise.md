# Week 1 Lab: Touch the Chain, Then Hand It to an Agent

**Weight:** counts toward weekly Labs. **Due:** before Week 2, Session 3. **Late turn-in accepted:** you can still submit after the deadline (marked late) — don't skip it.
**Prerequisite:** finish `resources/setup-guide.md` first.
**Note:** web3 is installed under **python3.11** — use `python3.11 xxx.py` for this lab. Scripts that write state (send/interact) need `anvil` running in another terminal first.

## Goal

First *touch* this objective world by hand (read + send + interact with a contract), then **wrap those operations as tools, add a guardrail, and hand them to an agent** — walking the full R1→R5 arc of Week 1.

## Track A — Main (everyone)

1. **Environment proof.** Paste into `reflection.md`:
   ```bash
   python3.11 --version
   forge --version
   python3.11 -c "import web3; print('web3', web3.__version__)"
   ```
   Plus a screenshot of MetaMask on **Base Sepolia** with some test ETH.
2. **Read the chain.** Run `code/read_chain.py`, paste the output. One sentence: *what did you read, and why did it cost nothing and need no login?*
3. **Send a native asset.** Start `anvil`, run `code/send_asset.py`, paste before/after balances. One sentence: *from pressing enter to the asset arriving, what steps did the transaction go through?*
4. **Interact with a contract (read + write).** Run `code/interact_contract.py`, paste the output. Answer: *what's the essential difference between `balanceOf` (read) and `transfer` (write) — why is one free and the other a transaction?*

## Track B — R5: Hand the operations to an agent (everyone does 5; 6 goes for A+)

5. **Tools + guardrail (run it yourself).** Run `code/agent_tools.py`, paste the output. Answer: *the two blocked calls (over-cap, and paying a stranger) — what stopped them, and why did "no transaction ever go out"?* Then lower the guard's `eth_cap` so a call that used to pass now gets blocked; paste before/after.
   > **This tier already earns solid credit** — you showed "tools + guardrail" work and can explain them.
6. **Wire up your own agent (for the A+).** Using `code/openclaw-agent.template.jsonc`, connect these tools to **OpenClaw** (check the official docs and turn the template into a real config). Give the agent one natural-language instruction (e.g., "check FRIEND's balance, then send it 1 ETH") and let it **call the tools and complete it within the guardrail**. **Paste a screenshot of the agent running** (instruction + tool calls + result).
   > **A working OpenClaw agent screenshot = A+.** If you can't get there, the Step-5 hand-run screenshot still earns credit.

## Deliverables (push to your repo)

- Your modified `read_chain.py` / `agent_tools.py` (your guard change)
- `reflection.md` (all Track A answers + screenshots; Track B: `agent_tools` output + guard before/after; for A+, the OpenClaw screenshot)

## Grading (12 pts)

| Criterion | Pts |
|-----------|-----|
| Environment proof complete (versions + MetaMask screenshot) | 3 |
| Read + send + interact all run, questions answered correctly | 4 |
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
