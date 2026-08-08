// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

abstract contract DiamondRoot {
    mapping(address account => uint256 amount) internal balances;
}

abstract contract DiamondPayments is DiamondRoot {
    function _pay(address payable recipient, uint256 amount) internal {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
    }
}

abstract contract DiamondAccounting is DiamondRoot {
    function _record(address account, uint256 amount) internal {
        balances[account] -= amount;
    }
}

