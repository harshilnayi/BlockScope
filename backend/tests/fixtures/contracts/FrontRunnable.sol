// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FrontRunnable {
    bytes32 public answerHash;
    address public owner;
    uint256 public reward;

    constructor(bytes32 _answerHash) payable {
        answerHash = _answerHash;
        owner = msg.sender;
        reward = msg.value;
    }

    // VULNERABLE: Anyone watching the mempool can copy _answer from a winning reveal tx and resubmit with higher gas
    function reveal(string calldata _answer) external {
        require(
            keccak256(abi.encodePacked(_answer)) == answerHash,
            "Wrong answer"
        );
        require(reward > 0, "Already claimed");
        uint256 payout = reward;
        reward = 0;
        // Front-runner intercepts here before original tx mines
        (bool ok, ) = msg.sender.call{value: payout}("");
        require(ok, "Transfer failed");
    }

    function updateAnswer(bytes32 _newHash) external {
        require(msg.sender == owner, "Not owner");
        answerHash = _newHash;
    }
}
