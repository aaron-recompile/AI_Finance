// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console2} from "forge-std/Script.sol";
import {MockERC20} from "../src/MockERC20.sol";
import {SimpleLend} from "../src/SimpleLend.sol";

/// Deploy a lending market: WETH (collateral) + USDC (borrow), initial price 2000.
/// After deployment, mint WETH to the deployer and inject USDC into the market for borrowing.
/// Local anvil usage:
///   export PRIVATE_KEY=0xac0974...ff80
///   forge script script/DeployLend.s.sol --rpc-url http://localhost:8545 --broadcast
contract DeployLend is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address me = vm.addr(pk);
        vm.startBroadcast(pk);

        MockERC20 weth = new MockERC20("Wrapped ETH", "WETH");
        MockERC20 usdc = new MockERC20("USD Coin", "USDC");
        SimpleLend lend = new SimpleLend(address(weth), address(usdc), 2000e18);

        // Inject 1 million USDC into the market for borrowing; give yourself 10 WETH as collateral
        usdc.mint(address(lend), 1_000_000e18);
        weth.mint(me, 10e18);
        weth.approve(address(lend), type(uint256).max);
        usdc.approve(address(lend), type(uint256).max); // to conveniently repay your own debt later

        vm.stopBroadcast();

        console2.log("WETH :", address(weth));
        console2.log("USDC :", address(usdc));
        console2.log("LEND :", address(lend));
        console2.log("price (should be 2000e18):", lend.price());
    }
}
