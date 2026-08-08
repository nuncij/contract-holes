// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ImportedBalances} from "./ImportedBalances.sol";
import {PaymentLibrary} from "./PaymentLibrary.sol";

contract ImportedVulnerable is ImportedBalances {
    function withdraw(address payable recipient, uint256 amount) external {
        PaymentLibrary.pay(recipient, amount);
        balances[msg.sender] -= amount;
    }
}

