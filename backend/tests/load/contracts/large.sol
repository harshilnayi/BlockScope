pragma solidity ^0.8.0;

contract Large {
    uint256 public value;

    function update(uint256 x) public {
        value = x;
    }
}
