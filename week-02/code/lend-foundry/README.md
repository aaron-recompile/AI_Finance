# SimpleLend —— 你自己的链上当铺(借贷 + 清算)

第 2 周第 4 课的旗舰合约。和 `amm-foundry` 平行:一个**真能部署、真能清算**的最小借贷市场。
对照 `../lend.py`(Python 直觉版)—— 同一套"健康因子"数学,这里搬上链。

## 合约在讲什么

- `deposit / withdraw`:存、取抵押品(WETH)。
- `borrow / repay`:借、还债(USDC)。借完/取完都要求 **HF ≥ 1**。
- `healthFactor(user)` = 抵押品价值 × 清算阈值(80%) ÷ 债务。`>1` 安全,`<1` 可被清算。
- `setPrice`:**教学用手动喂价**(模拟预言机),好在课堂上"当场把 ETH 价砍下去"制造清算。
- `liquidate(user)`:HF<1 时,清算人还清其债务,按 **110% 折价**端走抵押品(那 10% 是清算奖励)。

## 跑测试

```bash
export PATH="$HOME/.foundry/bin:$PATH"
forge test -vv
```
应看到 **5 passed**:存借算 HF、借太多被拒、价跌变可清算、清算端走抵押品、健康仓位不能清算。

## 本地 anvil 部署 + 当场制造一次清算

```bash
# 终端 A:anvil(开着别关)
anvil

# 终端 B:
export PATH="$HOME/.foundry/bin:$PATH"
export PRIVATE_KEY=0xac0974...ff80  # Anvil test key #0 (public, local only)
forge script script/DeployLend.s.sol --rpc-url http://localhost:8545 --broadcast
# 记下打印的 WETH / USDC / LEND 地址
```

然后用 `cast` 走一遍"开仓 → 砍价 → 看 HF 跌破 1":

```bash
L=<LEND 地址>;  W=<WETH 地址>;  RPC=http://localhost:8545

# 存 1 WETH、借 1000 USDC
cast send $W "approve(address,uint256)" $L 1000000000000000000 --rpc-url $RPC --private-key $PRIVATE_KEY
cast send $L "deposit(uint256)" 1000000000000000000            --rpc-url $RPC --private-key $PRIVATE_KEY
cast send $L "borrow(uint256)"  1000000000000000000000         --rpc-url $RPC --private-key $PRIVATE_KEY

# 读健康因子(应 1.6e18 = 1.6)
cast call $L "healthFactor(address)(uint256)" <你的地址> --rpc-url $RPC

# 预言机砍价:2000 → 1200
cast send $L "setPrice(uint256)" 1200000000000000000000 --rpc-url $RPC --private-key $PRIVATE_KEY

# 再读 HF(应 0.96e18 = 0.96 < 1 → 可清算)
cast call $L "healthFactor(address)(uint256)" <你的地址> --rpc-url $RPC
```

> `<你的地址>` = anvil 账户0 `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266`。
> HF 从 1.6 掉到 0.96,就是"被清算"发生前的那一刻。收工 `pkill anvil`。

## 依赖

本项目用 forge-std。若 clone 后 `lib/forge-std` 缺失,跑一次:
```bash
forge install foundry-rs/forge-std
```
