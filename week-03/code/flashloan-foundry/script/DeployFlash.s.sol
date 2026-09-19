// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";
import {SimpleAMM} from "../src/SimpleAMM.sol";
import {FlashLender} from "../src/FlashLender.sol";
import {Arbitrageur} from "../src/Arbitrageur.sol";

interface IToken {
    function mint(address, uint256) external;
    function approve(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
}

/// Deploy the flash-loan arbitrage demo on Base Sepolia, wired to the course tokens
/// tUSDC (borrowed) + MAX (the volatile asset, ETH-role, ~2000).
/// Two DEXes with a deliberate price gap: cheap 1950, dear 2050.
contract DeployFlash is Script {
    address constant MAX   = 0x22201343039BB6418546978b447a45ee49f8dAa5;
    address constant TUSDC = 0x6797beC4DC1D4444Fe81790c47e9FB91e491Ac69;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address me = vm.addr(pk);
        vm.startBroadcast(pk);

        // two independent DEXes (token0 = MAX [ETH-role], token1 = tUSDC)
        SimpleAMM cheap = new SimpleAMM(MAX, TUSDC);
        SimpleAMM dear  = new SimpleAMM(MAX, TUSDC);

        // seed liquidity to build the gap
        IToken(MAX).mint(me, 2000e18);
        IToken(TUSDC).mint(me, 4_000_000e18);
        IToken(MAX).approve(address(cheap), type(uint256).max);
        IToken(TUSDC).approve(address(cheap), type(uint256).max);
        IToken(MAX).approve(address(dear), type(uint256).max);
        IToken(TUSDC).approve(address(dear), type(uint256).max);

        cheap.addLiquidity(1000e18, 1_950_000e18); // 1 MAX = 1950 tUSDC (cheap)
        dear.addLiquidity(1000e18, 2_050_000e18);  // 1 MAX = 2050 tUSDC (dear)

        // flash lender, funded with tUSDC liquidity
        FlashLender lender = new FlashLender(TUSDC);
        IToken(TUSDC).mint(address(lender), 5_000_000e18);

        // the arbitrage bot (borrow tUSDC -> buy MAX cheap -> sell MAX dear -> repay)
        Arbitrageur arb = new Arbitrageur(address(lender), address(cheap), address(dear), MAX, TUSDC);

        vm.stopBroadcast();

        console.log("CHEAP ", address(cheap));
        console.log("DEAR  ", address(dear));
        console.log("LENDER", address(lender));
        console.log("ARB   ", address(arb));
    }
}
