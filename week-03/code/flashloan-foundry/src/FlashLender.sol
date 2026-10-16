// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @notice The borrower must implement this callback within the same transaction
interface IFlashBorrower {
    function onFlashLoan(uint256 amount, uint256 fee, bytes calldata data) external;
}

/// @title FlashLender —— minimal flash-loan lender
/// @notice Lend out funds → call back the borrower → by the end of the callback, principal + fee must be repaid, otherwise the whole thing reverts.
///         "Repaid within the same transaction" is guaranteed by that last require line plus the EVM's atomicity.
contract FlashLender {
    IERC20 public immutable token;
    uint256 public constant FEE_BPS = 5; // 0.05%

    constructor(address _token) {
        token = IERC20(_token);
    }

    function flashLoan(uint256 amount, address borrower, bytes calldata data) external {
        uint256 balBefore = token.balanceOf(address(this));
        require(balBefore >= amount, "not enough liquidity");
        uint256 fee = (amount * FEE_BPS) / 10000;

        token.transfer(borrower, amount);                 // 1) lend the money out
        IFlashBorrower(borrower).onFlashLoan(amount, fee, data); // 2) the borrower operates within this transaction

        // 3) after the callback returns, the pool must have recovered principal + fee, otherwise the whole thing reverts
        require(token.balanceOf(address(this)) >= balBefore + fee, "flash loan not repaid");
    }
}
