// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {SimpleLend} from "../src/SimpleLend.sol";
import {MockERC20} from "../src/MockERC20.sol";

contract SimpleLendTest is Test {
    SimpleLend lend;
    MockERC20 weth;
    MockERC20 usdc;

    address alice = address(0xA11CE);      // borrower
    address liquidator = address(0xB0B);   // liquidator

    function setUp() public {
        weth = new MockERC20("Wrapped ETH", "WETH");
        usdc = new MockERC20("USD Coin", "USDC");
        // Build the market: initial price 1 WETH = 2000 USDC
        lend = new SimpleLend(address(weth), address(usdc), 2000e18);

        // First inject USDC into the pool for people to borrow
        usdc.mint(address(lend), 1_000_000e18);

        // Alice has 1 WETH; the liquidator has a pile of USDC to repay debt
        weth.mint(alice, 1e18);
        usdc.mint(liquidator, 1_000_000e18);

        vm.prank(alice);
        weth.approve(address(lend), type(uint256).max);
        vm.prank(liquidator);
        usdc.approve(address(lend), type(uint256).max);
    }

    /// Deposit 1 WETH, borrow 1000 USDC → HF = 2000*0.8/1000 = 1.6
    function test_DepositBorrowHealthFactor() public {
        vm.startPrank(alice);
        lend.deposit(1e18);
        lend.borrow(1000e18);
        vm.stopPrank();

        assertEq(lend.debtOf(alice), 1000e18);
        assertEq(usdc.balanceOf(alice), 1000e18);         // received the loan
        assertEq(lend.healthFactor(alice), 1.6e18);        // 1.6
    }

    /// Borrowing too much (HF would be < 1) must be rejected
    function test_OverBorrowReverts() public {
        vm.startPrank(alice);
        lend.deposit(1e18);
        // 1 WETH @2000, threshold 80% → can support at most 1600 USDC of debt. Borrowing 1601 should fail.
        vm.expectRevert("would be unhealthy");
        lend.borrow(1601e18);
        vm.stopPrank();
    }

    /// Slash the price to 1200 → HF = 1200*0.8/1000 = 0.96 < 1 → liquidatable
    function test_PriceDropMakesLiquidatable() public {
        vm.startPrank(alice);
        lend.deposit(1e18);
        lend.borrow(1000e18);
        vm.stopPrank();

        assertGe(lend.healthFactor(alice), 1e18);          // healthy at first
        lend.setPrice(1200e18);                            // oracle: ETH drops to 1200
        assertLt(lend.healthFactor(alice), 1e18);          // now unhealthy
        assertEq(lend.healthFactor(alice), 0.96e18);       // exactly 0.96
    }

    /// Full liquidation: price drops → liquidator repays debt and takes collateral at a 110% discount
    function test_LiquidationSeizesCollateral() public {
        vm.startPrank(alice);
        lend.deposit(1e18);
        lend.borrow(1000e18);
        vm.stopPrank();

        lend.setPrice(1200e18); // trigger liquidatable state

        uint256 liqWethBefore = weth.balanceOf(liquidator);
        vm.prank(liquidator);
        lend.liquidate(alice);

        // The liquidator repaid 1000 USDC and should take 1000*1.1/1200 = 0.91666… WETH
        uint256 seized = weth.balanceOf(liquidator) - liqWethBefore;
        assertEq(seized, uint256(1000e18) * 11000 / 10000 * 1e18 / 1200e18);
        assertEq(lend.debtOf(alice), 0);                   // debt cleared to zero
        // Alice still has some collateral left (not all seized)
        assertGt(lend.collateralOf(alice), 0);
    }

    /// A healthy position cannot be liquidated
    function test_CannotLiquidateHealthy() public {
        vm.startPrank(alice);
        lend.deposit(1e18);
        lend.borrow(1000e18);
        vm.stopPrank();

        vm.prank(liquidator);
        vm.expectRevert("healthy, cannot liquidate");
        lend.liquidate(alice);
    }
}
