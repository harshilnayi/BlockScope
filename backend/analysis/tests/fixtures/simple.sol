// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SimpleStorage
 * @dev Simple storage contract for testing BlockScope analysis
 */
contract SimpleStorage {
    uint256 public storedData;

    event DataStored(uint256 data);

    /**
     * @dev Store a value
     * @param x The value to store
     */
    function set(uint256 x) public {
        storedData = x;
        emit DataStored(x);
    }

    /**
     * @dev Retrieve the stored value
     * @return The stored value
     */
    function get() public view returns (uint256) {
        return storedData;
    }
}
