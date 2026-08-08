// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Dependency} from "example/Dependency.sol";

contract Main is Dependency {
    function readInheritedValue() external view returns (uint256) {
        return inheritedValue;
    }

    function transform(uint256 input)
        internal
        pure
        override
        inheritedGuard
        returns (uint256)
    {
        return super.transform(input) + 1;
    }

    function transformed(uint256 input) external pure returns (uint256) {
        return transform(input);
    }
}
