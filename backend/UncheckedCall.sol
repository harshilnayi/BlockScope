// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract UncheckedCall {
    address[] public payees;
    mapping(address => uint256) public shares;
    uint256 public totalShares;

    // VULNERABLE (intentional): No access control on addPayee()
    function addPayee(address payee, uint256 share) external {
        payees.push(payee);
        shares[payee] = share;
        totalShares += share;
    }

    function distribute() external payable {
        uint256 total = msg.value;
        for (uint i = 0; i < payees.length; i++) {
            uint256 payment = (total * shares[payees[i]]) / totalShares;
            // VULNERABLE: .send() return value unchecked
            payees[i].send(payment);
        }
    }

    function emergencyWithdraw(address payable to) external {
        // VULNERABLE: .transfer() throws on >2300 gas but can fail on smart contract wallets
        to.transfer(address(this).balance);
    }
}
