// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Test} from "forge-std/Test.sol";
import {MockERC20} from "../src/MockERC20.sol";
import {SimpleAMM} from "../src/SimpleAMM.sol";
import {FlashLender} from "../src/FlashLender.sol";
import {Arbitrageur} from "../src/Arbitrageur.sol";

/// Acceptance template for the Week 3 assignment. Run:  forge test -vv
contract FlashLoanTest is Test {
    MockERC20 eth;
    MockERC20 usdc;
    SimpleAMM cheap;      // ETH cheap (~1950)
    SimpleAMM expensive;  // ETH expensive (~2050)
    FlashLender lender;
    Arbitrageur arb;

    address me = address(this);

    function setUp() public {
        eth = new MockERC20("ETH", "ETH");
        usdc = new MockERC20("USD Coin", "USDC");

        cheap = new SimpleAMM(address(eth), address(usdc));
        expensive = new SimpleAMM(address(eth), address(usdc));

        // Build two deep pools with a price gap (1000 ETH each)
        _seed(cheap, 1000e18, 1_950_000e18);      // price0In1 ≈ 1950
        _seed(expensive, 1000e18, 2_050_000e18);  // price0In1 ≈ 2050

        // Fill the lender with USDC
        lender = new FlashLender(address(usdc));
        usdc.mint(address(lender), 5_000_000e18);

        arb = new Arbitrageur(
            address(lender), address(cheap), address(expensive), address(eth), address(usdc)
        );
    }

    function _seed(SimpleAMM amm, uint256 a0, uint256 a1) internal {
        eth.mint(me, a0);
        usdc.mint(me, a1);
        eth.approve(address(amm), type(uint256).max);
        usdc.approve(address(amm), type(uint256).max);
        amm.addLiquidity(a0, a1);
    }

    /// Reasonable size: zero-capital arbitrage that produces a profit
    function test_ProfitableArb() public {
        assertEq(usdc.balanceOf(address(arb)), 0); // no capital before starting

        arb.run(20_000e18); // borrow 20k USDC to arbitrage

        uint256 profit = usdc.balanceOf(me); // profit sent back to owner (= this test contract)
        emit log_named_decimal_uint("net profit (USDC)", profit, 18);
        assertGt(profit, 0); // there is a net profit
    }

    /// Borrow too much: you flatten the gap yourself and can't repay → whole thing reverts (atomicity)
    function test_TooMuchReverts() public {
        vm.expectRevert(); // FlashLender / Arbitrageur require triggers the revert
        arb.run(2_000_000e18);
    }

    /// After the revert, the lender is not down a cent (proving "you didn't lose, only gas")
    function test_LenderUnharmedAfterRevert() public {
        uint256 before = usdc.balanceOf(address(lender));
        try arb.run(2_000_000e18) {
            fail();
        } catch {
            assertEq(usdc.balanceOf(address(lender)), before); // the pool is completely unharmed
        }
    }
}
