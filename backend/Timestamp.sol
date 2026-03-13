// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Timestamp {
    address[] public participants;
    address public owner;
    uint256 public ticketPrice = 0.01 ether;

    constructor() { owner = msg.sender; }

    function enter() external payable {
        require(msg.value == ticketPrice, "Wrong ticket price");
        participants.push(msg.sender);
    }

    function pickWinner() external {
        require(msg.sender == owner, "Not owner");
        require(participants.length > 0, "No participants");
        // VULNERABLE: block.timestamp is miner-influenceable
        uint256 index = uint256(
            keccak256(abi.encodePacked(block.timestamp))
        ) % participants.length;
        address winner = participants[index];
        (bool ok, ) = winner.call{value: address(this).balance}("");
        require(ok, "Payout failed");
        delete participants;
    }
}
