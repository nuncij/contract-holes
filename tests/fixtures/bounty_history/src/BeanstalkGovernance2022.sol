// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Reduction of same-transaction voting power; intentionally out of model.
contract BeanstalkGovernance2022Reduced {
    uint256 public totalVotingPower;
    mapping(address => uint256) public votingPower;
    mapping(bytes32 => uint256) public proposalVotes;

    function depositVotingPower(uint256 amount) external {
        votingPower[msg.sender] += amount;
        totalVotingPower += amount;
    }

    function vote(bytes32 proposal) external {
        proposalVotes[proposal] += votingPower[msg.sender];
    }

    function canEmergencyCommit(bytes32 proposal) external view returns (bool) {
        return proposalVotes[proposal] * 3 > totalVotingPower * 2;
    }
}

