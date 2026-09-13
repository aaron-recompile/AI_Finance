# Build Your Own Uniswap — Foundry 项目(第 2 周旗舰)

一个真能部署、真能兑换的最小 `x*y=k` AMM。对照同目录上一层的 `amm.py`(Python 直觉版)——同一套数学,这里是**链上合约**。

## 文件

| 文件 | 是什么 |
|------|--------|
| `src/SimpleAMM.sol` | AMM 合约:加/撤流动性、swap、0.3% 手续费、LP 份额、`x*y=k` |
| `src/MockERC20.sol` | 教学用最简 ERC20(可自由 mint,建池用) |
| `test/SimpleAMM.t.sol` | 验收测试:初始价、k 不减、滑点随单量增大、LP 赚手续费 |
| `script/DeployAMM.s.sol` | 部署到测试网 + 注入流动性 |

## 本地跑测试(不需要联网/私钥)

```bash
forge test -vv
```
预期:5 passed。这就是你作业的验收基线。

## 部署到测试网(Base Sepolia 为例)

```bash
export PRIVATE_KEY=0x你的测试网私钥   # 需有测试网 gas
forge script script/DeployAMM.s.sol --rpc-url https://sepolia.base.org --broadcast
```
输出会打印 tETH / tUSDC / AMM 三个地址,以及初始价(应 ≈ 2000e18)。

## 你的作业从这里开始

- 主轨:补 `add/removeLiquidity` 的边界、写更多测试、把滑点跑成一张表。
- 支轨:部署上去,用 `web3.py` 从链上兑换一次(见第 2 周 lab-exercise)。

> 数学吃不透就回去看 `amm.py` 和讲义的 `x*y=k` 推导。合约只是把那一行搬上链。

## 依赖

本项目用 forge-std。若 clone 后 `lib/forge-std` 缺失,跑一次:
```bash
forge install foundry-rs/forge-std
```
