pragma solidity ^0.8.25;

interface ICallback {
    function ping() external;
}

library PureLibrary {
    function increment(uint256 value) public pure returns (uint256) {
        return value + 1;
    }
}

type UserValue is uint256;

contract PrecisionCases {
    uint256 public balance;
    address public immutable fixedTarget;
    address public owner;
    mapping(address => bool) public admins;
    mapping(address => uint256) public preferences;

    constructor(address target) {
        fixedTarget = target;
        owner = msg.sender;
    }

    function callSemantics(uint256 raw) external pure returns (uint256) {
        UserValue value = UserValue.wrap(raw);
        return PureLibrary.increment(_pure(value) + _internal(value));
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

    function infeasibleBranchViaHelper(bool chooseCallback, address target) external {
        if (chooseCallback) {
            _ping(target);
        } else {
            balance = 2;
        }
    }

    function feasibleBranch(bool chooseCallback, address target) external {
        if (chooseCallback) {
            ICallback(target).ping();
            balance = 1;
        }
    }

    function postConditionalWrite(bool chooseCallback, address target) external {
        if (chooseCallback) {
            _ping(target);
        }
        balance = 3;
    }

    function fixedTargetStillNeedsReview() external {
        ICallback(fixedTarget).ping();
        balance = 1;
    }

    function fixedTargetAliasStillNeedsReview() external {
        address target = fixedTarget;
        ICallback(target).ping();
        balance = 4;
    }

    function fixedTargetHelperStillNeedsReview() external {
        _ping(fixedTarget);
        balance = 5;
    }

    function fixedTargetCall() external {
        ICallback(fixedTarget).ping();
    }

    function callerSelectedTarget(address target) external {
        ICallback(target).ping();
    }

    function roleProtectedWrite(address nextOwner) external {
        require(admins[msg.sender]);
        owner = nextOwner;
    }

    function callerOwnedWrite(uint256 value) external {
        preferences[msg.sender] = value;
    }

    function selfGrantRole() external {
        admins[msg.sender] = true;
    }

    function arbitraryAccountWrite(address account) external {
        admins[account] = true;
    }

    function _ping(address target) internal {
        ICallback(target).ping();
    }
}
