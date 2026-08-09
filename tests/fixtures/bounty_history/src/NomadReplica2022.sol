// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of the zero-root acceptance invariant; intentionally out of model.
contract NomadReplica2022Reduced {
    mapping(bytes32 => uint256) public confirmAt;
    mapping(bytes32 => bool) public processed;

    constructor(bytes32 initialRoot) {
        confirmAt[initialRoot] = 1;
    }

    function process(bytes32 root) external {
        require(confirmAt[root] != 0 && confirmAt[root] <= block.timestamp, "root");
        processed[root] = true;
    }
}

