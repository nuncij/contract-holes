// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of the uninitialized Wormhole implementation disclosure.
contract WormholeProxy2022Reduced {
    address public guardian;

    function initialize(address initialGuardian) external {
        guardian = initialGuardian;
    }

    function submitContractUpgrade(address target, bytes calldata data) external {
        require(msg.sender == guardian, "guardian only");
        (bool success, ) = target.delegatecall(data);
        require(success, "upgrade failed");
    }
}

