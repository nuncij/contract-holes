// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IPlugin {
    function run(bytes calldata payload) external;
}

contract TargetVulnerable {
    function arbitrary(address target, bytes calldata payload) external {
        address aliasTarget = target;
        (bool success, ) = aliasTarget.call(payload);
        require(success, "call failed");
    }

    function throughHelper(address target, bytes calldata payload) external {
        _dispatch(target, payload);
    }

    function upgrade(address implementation, bytes calldata payload) external {
        (bool success, ) = implementation.delegatecall(payload);
        require(success, "delegatecall failed");
    }

    function invoke(IPlugin plugin, bytes calldata payload) external {
        plugin.run(payload);
    }

    function _dispatch(address target, bytes calldata payload) internal {
        (bool success, ) = target.call(payload);
        require(success, "call failed");
    }
}

contract TargetSafe {
    address private immutable trustedTarget;
    IPlugin private immutable trustedPlugin;

    constructor(address target, IPlugin plugin) {
        trustedTarget = target;
        trustedPlugin = plugin;
    }

    function fixedTarget(bytes calldata payload) external {
        (bool success, ) = trustedTarget.call(payload);
        require(success, "call failed");
    }

    function fixedPlugin(bytes calldata payload) external {
        trustedPlugin.run(payload);
    }

    function payment(address payable recipient, uint256 amount) external {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
    }
}

