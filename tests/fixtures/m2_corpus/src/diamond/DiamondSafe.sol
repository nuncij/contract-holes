// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DiamondPayments, DiamondAccounting} from "./DiamondHierarchy.sol";

contract DiamondSafe is DiamondPayments, DiamondAccounting {
    function withdraw(address payable recipient, uint256 amount) external {
        _record(msg.sender, amount);
        _pay(recipient, amount);
    }
}

