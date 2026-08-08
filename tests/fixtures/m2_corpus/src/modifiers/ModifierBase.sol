// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

abstract contract ModifierBase {
    mapping(address account => uint256 amount) internal credits;
    uint256 private _status;

    modifier protected() {
        require(_status == 0, "reentrant call");
        _status = 1;
        _;
        _status = 0;
    }

    function _pay(address payable recipient, uint256 amount) internal {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "payment failed");
    }
}

