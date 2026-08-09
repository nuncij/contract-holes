// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Repository-owned target used only by the private M7 pilot.
contract AuthorizedPilotVault {
    address public immutable owner;
    uint256 public protectedCounter;

    constructor() {
        owner = msg.sender;
    }

    function privilegedAction() external {
        require(tx.origin == owner, "owner only");
        protectedCounter += 1;
    }

    /// @dev Deliberately best-effort and state-independent for triage practice.
    function diagnosticPing(address target, bytes calldata payload) external {
        target.call(payload);
    }
}
