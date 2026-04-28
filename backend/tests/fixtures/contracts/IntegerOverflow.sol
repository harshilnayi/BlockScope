// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract IntegerOverflow {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    constructor(uint256 _supply) {
        totalSupply = _supply;
        balances[msg.sender] = _supply;
    }

    function transfer(address to, uint256 amount) public {
        // VULNERABLE: No overflow check in Solidity 0.7
        require(balances[msg.sender] >= amount, "Balance too low");
        balances[msg.sender] -= amount;
        balances[to] += amount; // Can overflow on 0.7.x
    }

    function batchAirdrop(address[] memory recipients, uint256 perAmount) public {
        // VULNERABLE: recipients.length * perAmount can overflow
        uint256 total = recipients.length * perAmount;
        require(balances[msg.sender] >= total);
        for (uint i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += perAmount;
        }
        balances[msg.sender] -= total;
    }
}
