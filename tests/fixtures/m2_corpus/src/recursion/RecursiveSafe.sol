// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {RecursivePayments} from "./RecursivePayments.sol";

contract RecursiveSafe is RecursivePayments {
    function withdraw(address payable recipient, uint256 amount) external {
        balances[msg.sender] -= amount;
        _recursivePay(recipient, amount, 1);
    }
}

