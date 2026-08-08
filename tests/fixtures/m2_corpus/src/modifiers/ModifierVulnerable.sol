// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ModifierBase} from "./ModifierBase.sol";

contract ModifierVulnerable is ModifierBase {
    function withdraw(address payable recipient, uint256 amount) external {
        _pay(recipient, amount);
        credits[msg.sender] -= amount;
    }
}

