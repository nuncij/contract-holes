// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IIdleShareSupplyReduced {
    function totalSupply() external view returns (uint256);
}

/// Reduction of the mutable-supply integration assumption; intentionally out of model.
contract EnzymeIdle2021Reduced {
    uint256 public lastSharePrice;

    function valueShares(IIdleShareSupplyReduced idle, uint256 totalNav) external {
        lastSharePrice = totalNav / idle.totalSupply();
    }
}

