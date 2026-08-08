// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {RecursivePayments} from "./RecursivePayments.sol";

contract RecursiveVulnerable is RecursivePayments {
    function withdraw(address payable recipient, uint256 amount) external {
        _recursivePay(recipient, amount, 1);
        balances[msg.sender] -= amount;
    }
}

