// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ICreamHookTokenReduced {
    function transfer(address recipient, uint256 amount) external returns (bool);
}

/// Reduction of the transfer-hook reentrancy ordering reported by C.R.E.A.M.
contract CreamAmp2021Reduced {
    ICreamHookTokenReduced public immutable token;
    mapping(address => uint256) public accountBorrows;

    constructor(ICreamHookTokenReduced token_) {
        token = token_;
    }

    function borrow(uint256 amount) external {
        require(token.transfer(msg.sender, amount), "transfer failed");
        accountBorrows[msg.sender] += amount;
    }
}

