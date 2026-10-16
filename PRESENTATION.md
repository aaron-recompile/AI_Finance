# Track B Submission: Project Presentation Outline

## Slide 1: Executive Summary & Vision
- **Goal:** Build a robust, decoupled, and autonomous flash loan arbitrage agent on Base Sepolia.
- **Core Innovation:** Combining headless, safe smart-contract execution scripts with an integrated Streamlit Arena dashboard and natural language agent chat interface.

## Slide 2: Technical Architecture & Mechanics
- **AMM Routing:** Exploiting constant product price disparities between Pool A and Pool B.
- **Safety Controls:** Bounded batch execution (strict 10-shot safety cap), pre-execution profitability validation, and Web3 checksum compliance.
- **On-Chain Proof:** Successful execution verified on-chain (e.g., Tx Hash `0xdff9ef2caf650ce93a5cc73c15bde125b72a58eea8c57193093b427484a19785`).

## Slide 3: Unified Arena Dashboard (`app.py`)
- Real-time pool reserve and price gap monitoring.
- Wallet leaderboard tracking automatic profit delivery in tUSDC.
- Interactive agent chat interface (`st.chat_message`) translating user intent into precise CLI execution commands.

## Slide 4: Conclusion & Future Outlook
- Full decoupling of headless backend (`strategy.py`) and frontend dashboard (`app.py`).
- Scalable framework ready for multi-pool routing and automated high-frequency gas optimizations.