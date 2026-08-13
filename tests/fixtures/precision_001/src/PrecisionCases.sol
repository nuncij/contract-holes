pragma solidity ^0.8.25;

interface ICallback {
    function ping() external;
}

type UserValue is uint256;

contract PrecisionCases {
    uint256 public balance;
    address public immutable fixedTarget;
    address public owner;
    mapping(address => bool) public admins;

    constructor(address target) {
        fixedTarget = target;
        owner = msg.sender;
    }

    function callSemantics(uint256 raw) external pure returns (uint256) {
        UserValue value = UserValue.wrap(raw);
        return _pure(value) + _internal(value);
    }

    function _pure(UserValue value) internal pure returns (uint256) {
        return UserValue.unwrap(value);
    }

    function _internal(UserValue value) internal pure returns (uint256) {
        return UserValue.unwrap(value);
    }

    function infeasibleBranch(bool chooseCallback, address target) external {
        if (chooseCallback) {
            ICallback(target).ping();
        } else {
            balance = 1;
        }
    }

    function feasibleBranch(bool chooseCallback, address target) external {
        if (chooseCallback) {
            ICallback(target).ping();
            balance = 1;
        }
    }

    function fixedTargetStillNeedsReview() external {
        ICallback(fixedTarget).ping();
        balance = 1;
    }

    function fixedTargetCall() external {
        ICallback(fixedTarget).ping();
    }

    function callerSelectedTarget(address target) external {
        ICallback(target).ping();
    }

    function roleProtectedWrite(address nextOwner) external {
        require(msg.sender == owner);
        owner = nextOwner;
    }

    function callerOwnedWrite() external {
        admins[msg.sender] = true;
    }

    function arbitraryAccountWrite(address account) external {
        admins[account] = true;
    }
}
