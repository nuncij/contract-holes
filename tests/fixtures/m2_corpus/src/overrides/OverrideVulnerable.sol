// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {OverrideBase} from "./OverrideBase.sol";

contract OverrideVulnerable is OverrideBase {
    function withdraw(address payable recipient, uint256 amount) external override {
        _pay(recipient, amount);
        super._record(msg.sender, amount);
    }
}

