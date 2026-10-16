# 🛡️ Track B: Flash Loan Arbitrage Arena & Agent Chat Interface

An autonomous, dual-pool constant product AMM arbitrage system with flash loan mechanics deployed on **Base Sepolia**, featuring a unified Streamlit Arena dashboard and an interactive agent chat interface.

---

## 🏗️ Architecture & Mechanism
- **Pool A (Cheap):** `0xc76a02903a3cf4ef62decaea3021771a41271eb4`
- **Pool B (Dear):** `0x3d9f8ec22dc5fcc6b0e612d17e1df6bf5c879c8c`
- **Agent/Wallet Address:** `0xEd0bc13d45ED73e172701587fca854045F99c6c0`
- **Mechanism:** Dual-pool constant product AMM routing with fee deductions and flash loan mechanics. Profits are automatically routed and delivered directly to the user's wallet on-chain.

---

## 🚀 Quick Start Guide

### 1. Environment Setup
Clone or place this repository into your workspace and activate your virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt