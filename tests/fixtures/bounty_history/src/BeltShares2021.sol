// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of the accounting-baseline logic error; intentionally out of model.
contract BeltShares2021Reduced {
    uint256 public accountedAssets;
    uint256 public totalShares;

    function deposit(uint256 amount, uint256 observedAssets) external returns (uint256) {
        uint256 shares = totalShares == 0
            ? amount
            : amount * totalShares / observedAssets;
        accountedAssets += amount;
        totalShares += shares;
        return shares;
    }
}

