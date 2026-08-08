// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract AuthorizationVulnerable {
    address public owner;
    address public implementation;
    address public treasury;
    mapping(address => uint256) public balances;

    constructor(address initialOwner) {
        owner = initialOwner;
    }

    function changeOwner(address newOwner) external {
        owner = newOwner;
    }

    function upgrade(address newImplementation) external {
        _setImplementation(newImplementation);
    }

    function conditionalOwner(address newOwner, bool checkCaller) external {
        if (checkCaller) {
            require(msg.sender == owner, "not owner");
        }
        owner = newOwner;
    }

    function authorizeAfterWrite(address newTreasury) external {
        treasury = newTreasury;
        require(msg.sender == owner, "not owner");
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function _setImplementation(address newImplementation) internal {
        implementation = newImplementation;
    }
}

contract AuthorizationSafe {
    address public owner;
    address public implementation;
    address public treasury;
    mapping(address => bool) public admins;
    mapping(address => uint256) public balances;

    constructor(address initialOwner) {
        owner = initialOwner;
    }

    modifier restricted() {
        require(msg.sender == owner, "not owner");
        _;
    }

    function changeOwner(address newOwner) external restricted {
        owner = newOwner;
    }

    function upgrade(address newImplementation) external {
        require(msg.sender == owner, "not owner");
        _setImplementation(newImplementation);
    }

    function upgradeViaHelper(address newImplementation) external {
        _checkOwner();
        _setImplementation(newImplementation);
    }

    function setAdmin(address account, bool enabled) external restricted {
        admins[account] = enabled;
    }

    function setTreasury(address newTreasury) external restricted {
        treasury = newTreasury;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function _checkOwner() internal view {
        require(msg.sender == owner, "not owner");
    }

    function _setImplementation(address newImplementation) internal {
        implementation = newImplementation;
    }
}
