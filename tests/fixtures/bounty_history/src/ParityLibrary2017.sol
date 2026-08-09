// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Locally authored reduction of the Parity library incident; no upstream code copied.
contract ParityLibrary2017Reduced {
    address public owner;

    function initWallet() external {
        owner = msg.sender;
    }

    function kill(address payable recipient) external {
        require(msg.sender == owner, "owner only");
        selfdestruct(recipient);
    }
}

