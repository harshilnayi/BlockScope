// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Simulated Initializable base
abstract contract Initializable {
    bool private _initialized;
    modifier initializer() {
        require(!_initialized, "Already initialized");
        _initialized = true;
        _;
    }
}

contract VulnerableLogic is Initializable {
    address public owner;
    uint256 public treasuryBalance;

    // VULNERABLE: initializer is defined but never called
    // during deployment (no constructor calls initialize())
    function initialize(address _owner) public initializer {
        owner = _owner;
    }

    function deposit() external payable {
        treasuryBalance += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(msg.sender == owner, "Not owner");
        require(treasuryBalance >= amount, "Insufficient");
        treasuryBalance -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
    }

    // VULNERABLE: No owner check — storage can be manipulated
    function setTreasury(uint256 amount) external {
        // Anyone can call this since owner == address(0)
        treasuryBalance = amount;
    }
}

// Proxy that deploys logic but never calls initialize()
contract UnsafeProxy {
    address public implementation;

    constructor(address _impl) {
        implementation = _impl;
        // MISSING: IVulnerableLogic(_impl).initialize(msg.sender);
    }

    fallback() external payable {
        address impl = implementation;
        assembly {
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
