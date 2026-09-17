// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title SimpleAMM —— your own Uniswap (x*y=k constant-product market making + 0.3% fee)
/// @notice The flagship of Week 2: a minimal AMM that really deploys and really swaps.
///         Compare with amm.py (the Python intuition version) —— same math, here as an on-chain contract.
contract SimpleAMM {
    IERC20 public immutable token0;
    IERC20 public immutable token1;

    uint256 public reserve0;
    uint256 public reserve1;

    uint256 public totalShares;
    mapping(address => uint256) public shares;

    uint256 public constant FEE_BPS = 30; // 0.3%

    event LiquidityAdded(address indexed who, uint256 amount0, uint256 amount1, uint256 minted);
    event LiquidityRemoved(address indexed who, uint256 out0, uint256 out1, uint256 burned);
    event Swap(address indexed who, bool zeroForOne, uint256 amountIn, uint256 amountOut);

    constructor(address _token0, address _token1) {
        require(_token0 != _token1, "same token");
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }

    // ---- Liquidity ----

    /// Add liquidity: deposit both tokens at the current ratio, mint LP shares
    function addLiquidity(uint256 amount0, uint256 amount1) external returns (uint256 minted) {
        token0.transferFrom(msg.sender, address(this), amount0);
        token1.transferFrom(msg.sender, address(this), amount1);

        if (totalShares == 0) {
            minted = _sqrt(amount0 * amount1); // First LP: shares = sqrt(x*y)
        } else {
            // Subsequent LPs: mint by the smaller ratio (to avoid changing the price)
            minted = _min(
                (amount0 * totalShares) / reserve0,
                (amount1 * totalShares) / reserve1
            );
        }
        require(minted > 0, "zero shares");
        shares[msg.sender] += minted;
        totalShares += minted;
        reserve0 += amount0;
        reserve1 += amount1;
        emit LiquidityAdded(msg.sender, amount0, amount1, minted);
    }

    /// Remove liquidity: withdraw both tokens pro rata to your shares (including accrued fees → so you may get back more than you deposited)
    function removeLiquidity(uint256 burnShares) external returns (uint256 out0, uint256 out1) {
        require(shares[msg.sender] >= burnShares, "insufficient shares");
        out0 = (reserve0 * burnShares) / totalShares;
        out1 = (reserve1 * burnShares) / totalShares;
        shares[msg.sender] -= burnShares;
        totalShares -= burnShares;
        reserve0 -= out0;
        reserve1 -= out1;
        token0.transfer(msg.sender, out0);
        token1.transfer(msg.sender, out1);
        emit LiquidityRemoved(msg.sender, out0, out1, burnShares);
    }

    // ---- Swaps ----

    /// Quote: given amountIn, how much you can take out (including the 0.3% fee), without changing state
    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut)
        public
        pure
        returns (uint256)
    {
        require(amountIn > 0, "zero in");
        require(reserveIn > 0 && reserveOut > 0, "empty pool");
        uint256 amountInWithFee = amountIn * (10000 - FEE_BPS);
        return (amountInWithFee * reserveOut) / (reserveIn * 10000 + amountInWithFee);
    }

    /// Swap token0 for token1
    function swap0For1(uint256 amountIn) external returns (uint256 amountOut) {
        amountOut = getAmountOut(amountIn, reserve0, reserve1);
        token0.transferFrom(msg.sender, address(this), amountIn);
        token1.transfer(msg.sender, amountOut);
        reserve0 += amountIn;
        reserve1 -= amountOut;
        emit Swap(msg.sender, true, amountIn, amountOut);
    }

    /// Swap token1 for token0
    function swap1For0(uint256 amountIn) external returns (uint256 amountOut) {
        amountOut = getAmountOut(amountIn, reserve1, reserve0);
        token1.transferFrom(msg.sender, address(this), amountIn);
        token0.transfer(msg.sender, amountOut);
        reserve1 += amountIn;
        reserve0 -= amountOut;
        emit Swap(msg.sender, false, amountIn, amountOut);
    }

    // ---- Read-only ----

    function k() external view returns (uint256) {
        return reserve0 * reserve1;
    }

    /// How much token1 one token0 is worth (scaled by 1e18)
    function price0In1() external view returns (uint256) {
        require(reserve0 > 0, "empty");
        return (reserve1 * 1e18) / reserve0;
    }

    // ---- Utilities ----

    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }

    /// Babylonian square root (same as Uniswap v2)
    function _sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) {
            z = y;
            uint256 x = y / 2 + 1;
            while (x < z) {
                z = x;
                x = (y / x + x) / 2;
            }
        } else if (y != 0) {
            z = 1;
        }
    }
}
