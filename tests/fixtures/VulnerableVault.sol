// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract VulnerableVault {
    mapping(address => uint256) public balances;
    address public implementation;

    function privileged(address expected) external view returns (bool) {
        return tx.origin == expected;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        balances[msg.sender] -= amount;
    }

    function notify(address target, bytes calldata payload) external {
        target.call(payload);
    }

    function runImplementation(bytes calldata payload) external {
        implementation.delegatecall(payload);
    }

    function destroy(address payable recipient) external {
        selfdestruct(recipient);
    }

    function draw() external view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.timestamp, msg.sender)));
    }
}

