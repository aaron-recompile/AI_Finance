// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console2} from "forge-std/Script.sol";
import {MockERC20} from "../src/MockERC20.sol";
import {SimpleAMM} from "../src/SimpleAMM.sol";

/// Deploy to a testnet: two mock tokens + one AMM, and inject initial liquidity.
/// Usage (Base Sepolia as an example):
///   export PRIVATE_KEY=0x...        # your testnet private key (with test gas)
///   forge script script/DeployAMM.s.sol \
///     --rpc-url https://sepolia.base.org --broadcast
contract DeployAMM is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address me = vm.addr(pk);
        vm.startBroadcast(pk);

        MockERC20 eth = new MockERC20("Test ETH", "tETH");
        MockERC20 usdc = new MockERC20("Test USDC", "tUSDC");
        SimpleAMM amm = new SimpleAMM(address(eth), address(usdc));

        // Mint to yourself and build the pool: 100 tETH / 200,000 tUSDC
        eth.mint(me, 1000e18);
        usdc.mint(me, 2_000_000e18);
        eth.approve(address(amm), type(uint256).max);
        usdc.approve(address(amm), type(uint256).max);
        amm.addLiquidity(100e18, 200_000e18);

        vm.stopBroadcast();

        console2.log("tETH :", address(eth));
        console2.log("tUSDC:", address(usdc));
        console2.log("AMM  :", address(amm));
        console2.log("price0In1 (should be ~2000e18):", amm.price0In1());
    }
}
