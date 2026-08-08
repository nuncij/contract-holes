// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

abstract contract RecursivePayments {
    mapping(address account => uint256 amount) internal balances;

    function _recursivePay(address payable recipient, uint256 amount, uint256 depth)
        internal
    {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
        if (depth > 0) {
            _recursivePay(recipient, amount, depth - 1);
        }
    }
}

