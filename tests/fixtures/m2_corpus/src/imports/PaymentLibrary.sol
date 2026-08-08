// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library PaymentLibrary {
    function pay(address payable recipient, uint256 amount) internal {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
    }
}

