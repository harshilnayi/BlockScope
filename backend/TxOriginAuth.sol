// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TxOriginAuth {
    address public owner;

    constructor() payable {
        owner = msg.sender;
    }

    function transfer(address payable dest, uint256 amount) public {
        // VULNERABLE: tx.origin instead of msg.sender
        require(tx.origin == owner, "Not authorized");
        dest.transfer(amount);
    }

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    receive() external payable {}
}
