// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Logic contract — storage slot 0 = 'count', slot 1 = 'owner'
contract LogicV1 {
    uint256 public count;     // slot 0
    address public owner;     // slot 1

    function increment() public { count++; }
    function setOwner(address _o) public { owner = _o; }
}

// Proxy — storage slot 0 = 'implementation', slot 1 = 'proxyOwner'
contract VulnerableProxy {
    address public implementation; // slot 0  ← COLLIDES with LogicV1.count
    address public proxyOwner;     // slot 1  ← COLLIDES with LogicV1.owner

    constructor(address _impl) {
        implementation = _impl;
        proxyOwner = msg.sender;
    }

    fallback() external payable {
        address impl = implementation;
        assembly {
            // VULNERABLE: delegatecall executes logic in proxy's context
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
