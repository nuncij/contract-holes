// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ICounter {
    function ping() external returns (uint256);
}

library Errors {
    error BadValue(uint256 value);
    event Done(uint256 value);
    struct Data {
        uint256 value;
    }
}

contract CallKinds {
    uint256 public stored;
    ICounter public immutable counter;

    constructor(ICounter c) {
        counter = c;
    }

    function usesErrorAndEvent(uint256 v) external {
        if (v == 0) revert Errors.BadValue(v);
        Errors.Data memory d = Errors.Data(v);
        emit Errors.Done(d.value);
    }

    function realExternal() external {
        stored = counter.ping();
    }
}
