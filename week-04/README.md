# Week 4 — From Program to Agent (OpenClaw)

Your bots were a pair of **hands** you drove by hand. This week: a **brain** that runs them on its own, 24/7, behind a fence — a real autonomous agent you talk to on Telegram.

| What | Where |
|------|-------|
| 🖥️ **Slides** | [`slides/AI_Finance_Week4_OpenClaw.html`](slides/AI_Finance_Week4_OpenClaw.html) — open in a browser |
| 💬 **Demo prompts** | [`prompts/jarvis-demo-prompts.md`](prompts/jarvis-demo-prompts.md) — what to say to the agent, by lego |
| 🤖 **Example skills** | [`skills/`](skills/) — real `SKILL.md` recipes + the `USER.md` standing rules (sanitized) |

## The idea
**OpenClaw** is a self-hosted agent runtime: a **heartbeat** (wakes on a schedule), **skills** (your code, wrapped as recipes), an **LLM** (the judgment), and a **channel** (Telegram). You don't rewrite your bots — you **wrap** one as a `SKILL.md`, give the agent its `USER.md` facts, and talk to it.

**Brain judges, hands execute.** The LLM decides *whether / which / how-much-at-most* — it never sizes a trade, never signs, never sees the key. Every money action **plans → waits for your `confirm` → executes → verifies on-chain → reports**.

## Your lab
Wrap one lego (swap / lend / flash-arb) as a skill, drive the agent through a trade with the prompts, and try to break its fence. Screenshot the run.

**Golden rule: testnets only. A private key is everything — never paste it into a website, a chat, a shared file, or an agent's prompt.**
