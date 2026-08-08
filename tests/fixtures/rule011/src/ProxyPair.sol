// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract UnsafeImplementation {
    address public owner;
    uint256 public value;

    function initialize(address initialOwner, uint256 initialValue) external {
        owner = initialOwner;
        value = initialValue;
    }

    function setup(address initialOwner) external {
        _configure(initialOwner);
    }

    function _configure(address initialOwner) internal {
        owner = initialOwner;
    }
}

contract SafeImplementation {
    bool private initialized;
    address public owner;

    modifier initializer() {
        require(!initialized, "already initialized");
        initialized = true;
        _;
    }

    function initialize(address initialOwner) external initializer {
        owner = initialOwner;
    }
}

contract CustomGuardedImplementation {
    bool private initialized;
    address public owner;

    function setup(address initialOwner) external {
        require(!initialized, "already initialized");
        initialized = true;
        owner = initialOwner;
    }
}

contract UnsafeProxy {
    address public implementation;
    address public admin;

    function forward(bytes calldata data) external returns (bytes memory) {
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }
}

contract SafeProxy {
    bytes32 private constant IMPLEMENTATION_SLOT =
        0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc;

    function forward(bytes calldata data) external returns (bytes memory) {
        address implementation;
        assembly {
            implementation := sload(IMPLEMENTATION_SLOT)
        }
        (bool success, bytes memory result) = implementation.delegatecall(data);
        require(success, "delegatecall failed");
        return result;
    }
}

contract VaultUnsafeV1 {
    address public owner;
    uint256 public totalAssets;
}

contract VaultUnsafeV2 {
    uint256 public totalAssets;
    address public owner;
    uint256 public feeRate;
}

contract VaultSafeV1 {
    address public owner;
    uint256 public totalAssets;
}

contract VaultSafeV2 is VaultSafeV1 {
    uint256 public feeRate;
}
