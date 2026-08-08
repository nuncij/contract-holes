// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SafeVault {
    mapping(address => uint256) public balances;

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "transfer failed");
    }
}

