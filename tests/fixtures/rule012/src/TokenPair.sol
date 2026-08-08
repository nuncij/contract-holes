// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IERC20 {
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount)
        external
        returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface INonStandardToken {
    function transfer(address recipient, uint256 amount) external;
}

contract TokenVulnerable {
    mapping(address => uint256) public credits;

    function ignoredTransfer(IERC20 token, address recipient, uint256 amount) external {
        token.transfer(recipient, amount);
    }

    function nominalDeposit(IERC20 token, uint256 amount) external {
        require(
            token.transferFrom(msg.sender, address(this), amount),
            "transfer failed"
        );
        credits[msg.sender] += amount;
    }

    function nominalDepositViaHelper(IERC20 token, uint256 amount) external {
        _pull(token, amount);
        credits[msg.sender] += amount;
    }

    function _pull(IERC20 token, uint256 amount) internal {
        require(
            token.transferFrom(msg.sender, address(this), amount),
            "transfer failed"
        );
    }
}

contract TokenSafe {
    mapping(address => uint256) public credits;

    function checkedTransfer(IERC20 token, address recipient, uint256 amount) external {
        require(token.transfer(recipient, amount), "transfer failed");
    }

    function deltaDeposit(IERC20 token, uint256 amount) external {
        uint256 beforeBalance = token.balanceOf(address(this));
        require(
            token.transferFrom(msg.sender, address(this), amount),
            "transfer failed"
        );
        uint256 received = token.balanceOf(address(this)) - beforeBalance;
        credits[msg.sender] += received;
    }

    function nonReturningToken(
        INonStandardToken token,
        address recipient,
        uint256 amount
    ) external {
        token.transfer(recipient, amount);
    }
}
