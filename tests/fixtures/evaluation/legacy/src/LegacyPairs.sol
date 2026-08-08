// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract LegacyVulnerable {
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

    function ambiguousHash(string calldata first, string calldata second)
        external
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked(first, second));
    }
}

contract LegacySafe {
    using AddressCall for address;

    mapping(address => uint256) public balances;
    address public immutable notificationTarget;

    constructor(address target) {
        notificationTarget = target;
    }

    function privileged(address expected) external view returns (bool) {
        return msg.sender == expected;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
    }

    function notify(bytes calldata payload) external {
        (bool success, ) = notificationTarget.call(payload);
        require(success);
    }

    function runImplementation(bytes calldata payload) external returns (bytes memory) {
        return notificationTarget.functionCall(payload);
    }

    function destroy(address payable recipient) external pure returns (address) {
        return recipient;
    }

    function draw(bytes32 oracleRandomness) external pure returns (uint256) {
        return uint256(oracleRandomness);
    }

    function unambiguousHash(string calldata first, string calldata second)
        external
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(first, second));
    }
}

library AddressCall {
    function functionCall(address target, bytes memory payload)
        internal
        returns (bytes memory)
    {
        (bool success, bytes memory result) = target.call(payload);
        require(success);
        return result;
    }
}
