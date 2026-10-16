# Example agent skills (OpenClaw)

These are the **skills** our class agent (Jarvis) uses to run the Week-2 / Week-3 legos on-chain. Each `SKILL.md` is a plain-English **recipe** the LLM follows; the actual money-making code is your Week-3 `chain.py` + bots, unchanged.

| File | What |
|------|------|
| `USER.example.md` | The shared **facts + standing rules** every session reads. Copy to `USER.md`, fill in your own testnet wallet + addresses. **The standing rules are the fence — read them.** |
| `treasury-swap/SKILL.md` | Swap a course token (Week-2 AMM lego). |
| `treasury-lend/SKILL.md` | Read / manage a borrow position + explain alerts (Week-2 lending lego). |
| `treasury-flash-arb/SKILL.md` | Run a flash-loan arbitrage (Week-3 lego). |

## How it plugs into OpenClaw
Drop these in your agent's skills folder, put the Treasury section in your `USER.md`, and the heartbeat + your chat drive them. The LLM reads your words + the recipe, then calls your deterministic functions. **Brain judges, hands execute** — the model never sizes a trade, never signs, never sees the key.

## Sanitized for publishing
Wallet addresses, key-file paths and machine-specific paths here are **placeholders**. Fill them with your own **testnet** values. Never commit a private key, a real `USER.md` holding a live treasury wallet, or a `.env`.
