// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title TestContract
 * @dev Simple contract for end-to-end testing
 */
contract TestContract {
    uint256 public value;
    address public owner;
    
    event ValueChanged(uint256 newValue);
    event OwnerChanged(address newOwner);
    
    constructor() {
        owner = msg.sender;
        value = 0;
    }
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Not the owner");
        _;
    }
    
    /**
     * @dev Set a new value
     */
    function setValue(uint256 _value) public onlyOwner {
        value = _value;
        emit ValueChanged(_value);
    }
    
    /**
     * @dev Get the current value
     */
    function getValue() public view returns (uint256) {
        return value;
    }
    
    /**
     * @dev Transfer ownership
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
        emit OwnerChanged(newOwner);
    }
}
