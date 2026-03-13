// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SelfDestruct {
    uint256 public depositTotal;
    mapping(address => uint256) public deposits;

    function deposit() external payable {
        depositTotal += msg.value;
        deposits[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = deposits[msg.sender];
        require(amount > 0, "Nothing to withdraw");
        deposits[msg.sender] = 0;
        depositTotal -= amount;
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
    }

    function getContractBalance() public view returns (uint256) {
        // VULNERABLE: Assumes address(this).balance == depositTotal
        // A self-destruct attack can make balance > depositTotal
        return address(this).balance;
    }

    function invariantCheck() public view returns (bool) {
        // This invariant can be broken by forced ETH
        return address(this).balance == depositTotal;
    }
}
