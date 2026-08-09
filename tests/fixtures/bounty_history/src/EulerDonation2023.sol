// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of donate-without-health-check behavior; intentionally out of model.
contract EulerDonation2023Reduced {
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;

    function donateToReserves(uint256 amount) external {
        collateral[msg.sender] -= amount;
    }

    function liquidatable(address account) external view returns (bool) {
        return debt[account] > collateral[account];
    }
}

