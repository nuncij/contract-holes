// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of the uninitialized Harvest implementation disclosure.
contract HarvestProxy2021Reduced {
    address public governance;
    address public hardWorker;

    function initialize(address initialGovernance, address initialWorker) external {
        governance = initialGovernance;
        hardWorker = initialWorker;
    }

    function doHardWork(bytes calldata data) external {
        require(msg.sender == governance, "governance only");
        (bool success, ) = hardWorker.delegatecall(data);
        require(success, "work failed");
    }
}

