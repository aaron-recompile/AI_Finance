// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {Script, console} from "forge-std/Script.sol";

interface ISimpleAMM {
    function shares(address) external view returns (uint256);
    function reserve0() external view returns (uint256);
    function reserve1() external view returns (uint256);
    function removeLiquidity(uint256) external returns (uint256, uint256);
    function addLiquidity(uint256, uint256) external returns (uint256);
}
interface IToken {
    function mint(address, uint256) external;
    function approve(address, uint256) external returns (bool);
}

/// Reset the two DEXes back to a fresh 1950 / 2050 price gap (owner-only in practice: the sole LP).
contract ResetGap is Script {
    address constant MAX   = 0x22201343039BB6418546978b447a45ee49f8dAa5;
    address constant TUSDC = 0x6797beC4DC1D4444Fe81790c47e9FB91e491Ac69;
    address constant CHEAP = 0xfE366315A4A21d34F875a737612e3Fe860bCd7f9;
    address constant DEAR  = 0x41c58Dc7eed3597FcDA9Cc6E42F11eB97b98CEff;

    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address me = vm.addr(pk);
        vm.startBroadcast(pk);

        // drain both pools (we are the only LP)
        ISimpleAMM(CHEAP).removeLiquidity(ISimpleAMM(CHEAP).shares(me));
        ISimpleAMM(DEAR).removeLiquidity(ISimpleAMM(DEAR).shares(me));

        // top up + re-approve
        IToken(MAX).mint(me, 2000e18);
        IToken(TUSDC).mint(me, 4_000_000e18);
        IToken(MAX).approve(CHEAP, type(uint256).max);
        IToken(TUSDC).approve(CHEAP, type(uint256).max);
        IToken(MAX).approve(DEAR, type(uint256).max);
        IToken(TUSDC).approve(DEAR, type(uint256).max);

        // re-seed the gap
        ISimpleAMM(CHEAP).addLiquidity(1000e18, 1_950_000e18); // 1950
        ISimpleAMM(DEAR).addLiquidity(1000e18, 2_050_000e18);  // 2050

        vm.stopBroadcast();

        console.log("CHEAP r0/r1", ISimpleAMM(CHEAP).reserve0(), ISimpleAMM(CHEAP).reserve1());
        console.log("DEAR  r0/r1", ISimpleAMM(DEAR).reserve0(), ISimpleAMM(DEAR).reserve1());
    }
}
