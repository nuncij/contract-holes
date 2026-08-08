// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library RecoveryLib {
    function recover(
        bytes32 digest,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) internal pure returns (address signer) {
        signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
    }
}

contract SignatureVulnerable {
    address public immutable owner;
    uint256 public executions;
    mapping(address => uint256) public nonces;

    constructor(address initialOwner) {
        require(initialOwner != address(0), "zero owner");
        owner = initialOwner;
    }

    function executeWeak(
        bytes32 action,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 digest = keccak256(abi.encode(action));
        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "bad signer");
        executions += 1;
    }

    function executeReplayable(
        bytes32 action,
        uint256 suppliedNonce,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        bytes32 digest = keccak256(
            abi.encode(block.chainid, address(this), action, suppliedNonce, deadline)
        );
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "bad signer");
        // A nonce-looking write is not replay protection when the digest uses caller data.
        nonces[owner] += 1;
        executions += 1;
    }

    function executeNoDeadline(
        bytes32 action,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        uint256 nonce = nonces[owner];
        bytes32 digest = keccak256(
            abi.encode(block.chainid, address(this), action, nonce)
        );
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function executeReversedDeadline(
        bytes32 action,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp >= deadline, "not active");
        uint256 nonce = nonces[owner];
        bytes32 digest = keccak256(
            abi.encode(block.chainid, address(this), action, nonce, deadline)
        );
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function executeWeakDomain(
        bytes32 action,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        uint256 nonce = nonces[owner];
        bytes32 digest = keccak256(abi.encode(action, nonce, deadline));
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function executeUncheckedRecovery(
        bytes32 action,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        uint256 nonce = nonces[owner];
        bytes32 digest = keccak256(
            abi.encode(block.chainid, address(this), action, nonce, deadline)
        );
        address signer = ecrecover(digest, v, r, s);
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function executeThroughHelper(
        bytes32 action,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        address signer = _recoverWeak(action, v, r, s);
        require(signer == owner, "bad signer");
        executions += 1;
    }

    function _recoverWeak(
        bytes32 action,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) internal pure returns (address) {
        bytes32 digest = keccak256(abi.encode(action));
        return ecrecover(digest, v, r, s);
    }
}

contract SignatureSafe {
    bytes32 private constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(uint256 chainId,address verifyingContract)"
    );
    bytes32 private constant ACTION_TYPEHASH = keccak256(
        "Action(bytes32 action,uint256 nonce,uint256 deadline)"
    );
    address public immutable owner;
    uint256 public executions;
    mapping(address => uint256) public nonces;

    constructor(address initialOwner) {
        require(initialOwner != address(0), "zero owner");
        owner = initialOwner;
    }

    function executeSafe(
        bytes32 action,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        uint256 nonce = nonces[owner];
        bytes32 structHash = keccak256(
            abi.encode(ACTION_TYPEHASH, action, nonce, deadline)
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", _domainSeparator(), structHash)
        );
        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "invalid signature");
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function recoverOnly(
        bytes32 digest,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external pure returns (address) {
        return ecrecover(digest, v, r, s);
    }

    function executeSafeThroughLibrary(
        bytes32 action,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(block.timestamp <= deadline, "expired");
        uint256 nonce = nonces[owner];
        bytes32 structHash = keccak256(
            abi.encode(ACTION_TYPEHASH, action, nonce, deadline)
        );
        bytes32 digest = keccak256(
            abi.encodePacked("\x19\x01", _domainSeparator(), structHash)
        );
        address signer = RecoveryLib.recover(digest, v, r, s);
        require(signer == owner, "bad signer");
        nonces[owner] = nonce + 1;
        executions += 1;
    }

    function diagnosticAndCount(
        bytes32 digest,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        address recovered = ecrecover(digest, v, r, s);
        if (recovered != address(0)) {
            executions += 1;
        }
    }

    function _domainSeparator() internal view returns (bytes32) {
        return keccak256(
            abi.encode(DOMAIN_TYPEHASH, block.chainid, address(this))
        );
    }
}
