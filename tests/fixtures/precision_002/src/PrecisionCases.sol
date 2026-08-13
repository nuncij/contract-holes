// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

interface ICallback {
    function ping() external;
    function viewValue() external view returns (uint256);
    function setValue(uint256 value) external;
}

interface IFeed {
    function latestPrice() external view returns (uint256);
}

interface IGovernance {
    function getTargets() external view returns (address[] memory);
}

interface IToken {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IReachable {
    function poke() external;
}

contract CloneTarget {
    function initialize(bytes calldata) external {}
}

contract CallbackClone {
    IReachable public reachable;

    constructor(IReachable target) {
        reachable = target;
        target.poke();
    }

    function initialize(bytes calldata) external {
        reachable.poke();
    }
}

contract PrecisionCases {
    uint256 public stateValue;
    address public owner;
    address public pendingOwner;
    uint256 public pendingOwnerDeadline;
    address public immutable fixedModule;
    IToken public immutable asset;
    mapping(address => bool) public registered;
    mapping(uint256 => bool) public readKeys;
    uint256 public unrelatedFlag;

    constructor(address module, IToken underlying) {
        fixedModule = module;
        asset = underlying;
        owner = msg.sender;
    }

    function viewThenWrite(address target) external {
        ICallback(target).viewValue();
        stateValue = 1;
    }

    function stateChangingThenWrite(address target) external {
        ICallback(target).setValue(1);
        stateValue = 2;
    }

    function writeThenInteract(address target) external {
        stateValue = 3;
        ICallback(target).ping();
    }

    function proposeOwner(address candidate) external {
        require(msg.sender == owner, "not owner");
        pendingOwner = candidate;
        pendingOwnerDeadline = block.timestamp + 2 days;
    }

    modifier onlyAfterDelay() {
        require(pendingOwner != address(0), "no pending owner");
        require(block.timestamp >= pendingOwnerDeadline, "delay not elapsed");
        _;
    }

    function acceptOwner() external onlyAfterDelay {
        owner = pendingOwner;
        pendingOwner = address(0);
        pendingOwnerDeadline = 0;
    }

    function unprotectedWrite(address nextOwner) external {
        owner = nextOwner;
    }

    function notYetElapsedWrite(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp < pendingOwnerDeadline, "not elapsed");
        owner = nextOwner;
    }

    function timestampEqualityWrite(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp == pendingOwnerDeadline, "exact");
        owner = nextOwner;
    }

    function timestampInequalityWrite(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp != pendingOwnerDeadline, "not exact");
        owner = nextOwner;
    }

    function unrelatedStateComparisonWithElapsed(address nextOwner) external {
        require(owner == address(0), "already initialized");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = nextOwner;
    }

    function unrelatedNonzeroFlagWithElapsed(address nextOwner) external {
        require(unrelatedFlag != 0, "flag not set");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = nextOwner;
    }

    function timestampOnlyWrite(address nextOwner) external {
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = nextOwner;
    }

    function optionalElapsedWrite(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(
            block.timestamp >= pendingOwnerDeadline || nextOwner != address(0),
            "optional delay"
        );
        owner = nextOwner;
    }

    function timelockDoesNotAuthorizeInput(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = nextOwner;
        pendingOwner = address(0);
        pendingOwnerDeadline = 0;
    }

    function registerClone(bytes calldata args) external {
        CloneTarget clone = new CloneTarget();
        clone.initialize(args);
        registered[address(clone)] = true;
    }

    function registerCallbackClone(IReachable reachable, bytes calldata args) external {
        CallbackClone clone = new CallbackClone(reachable);
        clone.initialize(args);
        registered[address(clone)] = true;
    }

    function registerExisting(CloneTarget existing, bytes calldata args) external {
        existing.initialize(args);
        registered[address(existing)] = true;
    }

    function executeGovernance() external {
        address[] memory targets = IGovernance(fixedModule).getTargets();
        for (uint256 i = 0; i < targets.length; i++) {
            (bool success, ) = targets[i].delegatecall(abi.encodeWithSignature("exec()"));
            require(success, "delegatecall failed");
        }
    }

    function executeCallerSelected(address module) external {
        address[] memory targets = IGovernance(module).getTargets();
        for (uint256 i = 0; i < targets.length; i++) {
            (bool success, ) = targets[i].delegatecall(abi.encodeWithSignature("exec()"));
            require(success, "delegatecall failed");
        }
    }

    function queryPrice(address feed) external view returns (uint256) {
        return IFeed(feed).latestPrice();
    }

    function queryThenUseAsMappingKey(address feed) external {
        readKeys[IFeed(feed).latestPrice()] = true;
    }

    function queryThenFeedExternalCall(address feed, address target) external {
        ICallback(target).setValue(IFeed(feed).latestPrice());
    }

    function queryPriceThenWrite(address feed) external {
        uint256 price = IFeed(feed).latestPrice();
        stateValue = price;
    }

    function deposit(uint256 amount) external {
        require(asset.transferFrom(msg.sender, address(this), amount));
    }

    function depositCallerAsset(IToken token, uint256 amount) external {
        require(token.transferFrom(msg.sender, address(this), amount));
    }

    function timelockDeadlineDoesNotAuthorizeWrite() external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = address(uint160(pendingOwnerDeadline));
    }

    function timelockLocalReadDoesNotAuthorizeInput(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        address observed = pendingOwner;
        require(observed != address(0), "observed");
        owner = nextOwner;
    }

    function timelockActionDoesNotAuthorizeLaterInput(address nextOwner) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = pendingOwner;
        pendingOwner = nextOwner;
    }

    function timelockMixedValueDoesNotAuthorizeInput(
        bool usePending,
        address nextOwner
    ) external {
        require(pendingOwner != address(0), "no pending");
        require(block.timestamp >= pendingOwnerDeadline, "elapsed");
        owner = usePending ? pendingOwner : nextOwner;
    }
}
