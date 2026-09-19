// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {SimpleAMM} from "./SimpleAMM.sol";

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
}

interface IFlashLender {
    function flashLoan(uint256 amount, address borrower, bytes calldata data) external;
}

/// @title Arbitrageur —— your flash-loan bot (the real on-chain version)
/// @notice Borrow USDC → buy ETH in the cheap pool → sell ETH in the expensive pool → repay principal + fee → profit stays in the contract.
///         All within one transaction; if you can't repay, FlashLender makes the whole thing revert (you only lose gas).
contract Arbitrageur {
    IFlashLender public immutable lender;
    SimpleAMM public immutable cheap;      // the pool where ETH is cheap
    SimpleAMM public immutable expensive;  // the pool where ETH is expensive
    IERC20 public immutable eth;           // token0
    IERC20 public immutable usdc;          // token1 = the borrowed money
    address public owner;

    constructor(address _lender, address _cheap, address _expensive, address _eth, address _usdc) {
        lender = IFlashLender(_lender);
        cheap = SimpleAMM(_cheap);
        expensive = SimpleAMM(_expensive);
        eth = IERC20(_eth);
        usdc = IERC20(_usdc);
        owner = msg.sender;
    }

    /// Start the arbitrage: borrow borrowUsdc
    function run(uint256 borrowUsdc) external {
        lender.flashLoan(borrowUsdc, address(this), "");
        // Reaching here means it's repaid; the profit (USDC) stays in this contract, withdraw it to owner
        usdc.transfer(owner, usdc.balanceOf(address(this)));
    }

    /// FlashLender calls back here after lending —— the actual arbitrage logic
    function onFlashLoan(uint256 amount, uint256 fee, bytes calldata) external {
        require(msg.sender == address(lender), "only lender");

        // 1) Cheap pool: USDC -> ETH (swap1For0, input token1=USDC)
        usdc.approve(address(cheap), amount);
        uint256 ethOut = cheap.swap1For0(amount);

        // 2) Expensive pool: ETH -> USDC (swap0For1, input token0=ETH)
        eth.approve(address(expensive), ethOut);
        uint256 usdcBack = expensive.swap0For1(ethOut);

        // 3) Repay principal + fee (if short, FlashLender's require makes the whole thing revert)
        require(usdcBack >= amount + fee, "arb not profitable -> revert");
        usdc.transfer(address(lender), amount + fee);
        // Whatever remains is the profit, kept in this contract
    }
}
