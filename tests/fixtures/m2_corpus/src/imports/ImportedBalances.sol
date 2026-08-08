// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

abstract contract ImportedBalances {
    mapping(address account => uint256 amount) internal balances;
}

