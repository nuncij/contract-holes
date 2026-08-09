// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Solidity-side reduction of the delegatecall entry involved in the Aurora Engine bug.
contract AuroraInflation2022Reduced {
    function delegatedExit(address exitPrecompile, bytes calldata data) external {
        (bool success, ) = exitPrecompile.delegatecall(data);
        require(success, "exit failed");
    }
}

