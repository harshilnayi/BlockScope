// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DOS{
    address[] public contributors;
    mapping(address => uint256) public contributions;
    uint256 public goal;
    bool public goalReached;

    constructor(uint256 _goal) { goal = _goal; }

    function contribute() external payable {
        if (contributions[msg.sender] == 0) {
            contributors.push(msg.sender); // Attacker can bloat this array
        }
        contributions[msg.sender] += msg.value;
        if (address(this).balance >= goal) goalReached = true;
    }

    function refundAll() external {
        // VULNERABLE: Unbounded loop — O(n) over contributors array
        require(!goalReached, "Goal was reached");
        for (uint i = 0; i < contributors.length; i++) {
            address payable c = payable(contributors[i]);
            uint256 amount = contributions[c];
            contributions[c] = 0;
            c.transfer(amount);  // Also uses deprecated .transfer()
        }
    }
}
