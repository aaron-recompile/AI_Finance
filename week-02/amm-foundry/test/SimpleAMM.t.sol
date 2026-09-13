// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {MockERC20} from "../src/MockERC20.sol";
import {SimpleAMM} from "../src/SimpleAMM.sol";

/// Acceptance test template for the Week 2 assignment. Run:  forge test -vv
contract SimpleAMMTest is Test {
    MockERC20 eth;
    MockERC20 usdc;
    SimpleAMM amm;

    address alice = address(0xA11CE); // liquidity provider
    address bob = address(0xB0B);     // trader

    function setUp() public {
        eth = new MockERC20("ETH", "ETH");
        usdc = new MockERC20("USD Coin", "USDC");
        amm = new SimpleAMM(address(eth), address(usdc));

        // alice builds the pool: 100 ETH / 200,000 USDC  → 1 ETH = 2000 USDC
        eth.mint(alice, 100e18);
        usdc.mint(alice, 200_000e18);
        vm.startPrank(alice);
        eth.approve(address(amm), type(uint256).max);
        usdc.approve(address(amm), type(uint256).max);
        amm.addLiquidity(100e18, 200_000e18);
        vm.stopPrank();

        // bob takes some ETH to swap
        eth.mint(bob, 50e18);
        vm.prank(bob);
        eth.approve(address(amm), type(uint256).max);
    }

    function test_InitialReservesAndPrice() public view {
        assertEq(amm.reserve0(), 100e18);
        assertEq(amm.reserve1(), 200_000e18);
        assertEq(amm.price0In1(), 2000e18); // 1 ETH = 2000 USDC
    }

    /// k only increases, never decreases (fees stay in the pool → k rises slightly)
    function test_SwapNeverDecreasesK() public {
        uint256 kBefore = amm.k();
        vm.prank(bob);
        uint256 out = amm.swap0For1(5e18);
        assertGt(out, 0);
        assertEq(usdc.balanceOf(bob), out);
        assertGe(amm.k(), kBefore); // key invariant
    }

    /// Larger orders get a worse unit price —— slippage grows with order size
    function test_SlippageGrowsWithSize() public view {
        uint256 outSmall = amm.getAmountOut(1e18, 100e18, 200_000e18);
        uint256 outBig = amm.getAmountOut(20e18, 100e18, 200_000e18);
        // USDC received per 1 ETH: the big order gets less
        assertLt(outBig / 20, outSmall / 1);
    }

    /// LP earns fees: after a bunch of back-and-forth swaps, the value alice withdraws > what she deposited
    function test_LpEarnsFees() public {
        // bob swaps back and forth repeatedly, pumping fees into the pool
        eth.mint(bob, 500e18);
        usdc.mint(bob, 1_000_000e18);
        vm.startPrank(bob);
        eth.approve(address(amm), type(uint256).max);
        usdc.approve(address(amm), type(uint256).max);
        for (uint256 i = 0; i < 20; i++) {
            uint256 got = amm.swap0For1(5e18);
            amm.swap1For0(got); // swap back, just to charge fees repeatedly
        }
        vm.stopPrank();

        // alice withdraws everything
        uint256 aliceShares = amm.shares(alice);
        vm.prank(alice);
        (uint256 out0, uint256 out1) = amm.removeLiquidity(aliceShares);

        // The combined value of the ETH+USDC she gets back should be >= what she deposited (accrued fees)
        // Simple measure: total value (at the initial price of 2000) is no less than the 400,000 USDC equivalent deposited
        uint256 valueOut = out1 + out0 * 2000;
        assertGe(valueOut, 400_000e18);
    }

    function test_RevertOnEmptyQuote() public {
        vm.expectRevert();
        amm.getAmountOut(1e18, 0, 200_000e18);
    }
}
