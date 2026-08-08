// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract Dependency {
    uint256 internal inheritedValue;

    modifier inheritedGuard() {
        _;
    }

    function transform(uint256 input) internal pure virtual returns (uint256) {
        return input;
    }
}
