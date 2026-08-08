// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {OverrideBase} from "./OverrideBase.sol";

contract OverrideSafe is OverrideBase {
    function withdraw(address payable recipient, uint256 amount) external override {
        super._record(msg.sender, amount);
        _pay(recipient, amount);
    }
}

