# BlockScope — Smart Contract Vulnerability Scanner
## Sample Test Contracts & Expected Results

<!-- ============================================================
     DOCUMENT METADATA
     Repository : github.com/harshilnayi/BlockScope
     Type       : QA Test Suite — 10 Sample Contracts
     Solidity   : 0.7.x, 0.8.x (^0.8.0 to ^0.8.20)
     Date       : March 2026
     ============================================================ -->

---

## 1. Overview

This document provides 10 sample Solidity smart contracts designed to test the BlockScope vulnerability scanner. Each contract targets a specific vulnerability class commonly detected by ML-powered and static-analysis-based smart contract security tools. For each contract, the expected scanner output, detected vulnerabilities (including severity and line numbers), risk score, and recommended remediation are provided.

These test cases can be used for:

- Regression testing after scanner model updates
- Validating detection accuracy (true positive rate)
- Demonstrating scanner capabilities to stakeholders
- Training developers to recognize and fix common vulnerabilities

---

## 2. Test Suite Summary

<!-- Overall pass/fail and average risk score across all 10 contracts -->

| Total Contracts | Passed | Failed | Avg Risk Score |
|:-:|:-:|:-:|:-:|
| 10 | 0 | 10 | 72/100 |

**Severity Distribution: 3 CRITICAL • 4 HIGH • 3 MEDIUM**

---

## 3. Quick Reference

<!-- One-line summary of each contract: vulnerability type, severity, risk score, and result -->

| # | Contract Name | Vulnerability Category | Severity | Risk Score | Result |
|:-:|---|---|:-:|:-:|:-:|
| 1 | `ReentrancyVault.sol` | Reentrancy Attack | CRITICAL | 95/100 | ✘ FAIL |
| 2 | `IntegerOverflow.sol` | Integer Overflow / Underflow | HIGH | 78/100 | ✘ FAIL |
| 3 | `FrontRunnable.sol` | Front-Running / MEV Vulnerability | HIGH | 74/100 | ✘ FAIL |
| 4 | `Timestamp.sol` | Block Timestamp Manipulation | MEDIUM | 55/100 | ✘ FAIL |
| 5 | `UncheckedCall.sol` | Unchecked Return Values | HIGH | 68/100 | ✘ FAIL |
| 6 | `TxOriginAuth.sol` | tx.origin Authentication Bypass | HIGH | 72/100 | ✘ FAIL |
| 7 | `SelfDestruct.sol` | Selfdestruct / Forceful ETH Injection | MEDIUM | 50/100 | ✘ FAIL |
| 8 | `VulnerableProxy.sol` | Delegatecall Storage Collision | CRITICAL | 92/100 | ✘ FAIL |
| 9 | `DOS.sol` | Denial of Service (Gas Griefing) | MEDIUM | 52/100 | ✘ FAIL |
| 10 | `UnsafeProxy.sol` | Uninitialized Storage Pointer / Missing Initializer | CRITICAL | 91/100 | ✘ FAIL |

---

## 4. Detailed Contract Analysis

<!-- ============================================================
     Each contract section follows this structure:
       - Category / Severity / Risk Score header
       - Description of the vulnerability scenario
       - Annotated Solidity source code
       - Expected scanner result (pass/fail + count)
       - Vulnerability table (name, severity, line, description)
       - Recommendation for remediation
     ============================================================ -->

---

### Contract 1: ReentrancyVault.sol

<!-- Severity: CRITICAL | Risk Score: 95/100 -->
**Category:** Reentrancy Attack | **Severity:** CRITICAL | **Risk Score:** 95/100

#### Description
An Ether vault where users can deposit and withdraw funds. The `withdraw` function updates the balance **after** the external call, creating a classic reentrancy vulnerability.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ReentrancyVault {

    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // VULNERABLE: External call made before state update
        // An attacker's fallback function can re-enter withdraw() here
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        balances[msg.sender] -= amount; // State update AFTER call — too late
    }

    receive() external payable {}
}
```

#### Expected Scanner Result

> **FAIL — 1 CRITICAL vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Reentrancy | CRITICAL | 14 | External call (`msg.sender.call`) made before balance state update. An attacker's fallback function can re-enter `withdraw()` and drain the contract. |

#### Recommendation
Apply the **Checks-Effects-Interactions** pattern: decrement balance before the external call, or use `ReentrancyGuard` from OpenZeppelin.

---

### Contract 2: IntegerOverflow.sol

<!-- Severity: HIGH | Risk Score: 78/100 -->
**Category:** Integer Overflow / Underflow | **Severity:** HIGH | **Risk Score:** 78/100

#### Description
A token contract using Solidity 0.7.x where arithmetic operations can overflow/underflow. SafeMath is not used, leaving the contract exposed to wrap-around attacks.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

// NOTE: Solidity <0.8.0 does NOT have built-in overflow protection

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
        balances[to] += amount; // Can silently overflow on 0.7.x
    }

    function batchAirdrop(address[] memory recipients, uint256 perAmount) public {
        // VULNERABLE: recipients.length * perAmount can overflow before require check
        uint256 total = recipients.length * perAmount;
        require(balances[msg.sender] >= total);
        for (uint i = 0; i < recipients.length; i++) {
            balances[recipients[i]] += perAmount;
        }
        balances[msg.sender] -= total;
    }
}
```

#### Expected Scanner Result

> **FAIL — 2 HIGH vulnerabilities detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Integer Overflow | HIGH | 16 | `balances[to] += amount` can silently overflow in Solidity <0.8.0, creating tokens out of thin air. |
| Integer Overflow (Multiplication) | HIGH | 22 | `recipients.length * perAmount` multiplication can overflow before the `require` check is evaluated. |

#### Recommendation
Upgrade to Solidity `>=0.8.0` where overflow/underflow revert by default, or use OpenZeppelin's `SafeMath` library.

---

### Contract 3: FrontRunnable.sol

<!-- Severity: HIGH | Risk Score: 74/100 -->
**Category:** Front-Running / MEV Vulnerability | **Severity:** HIGH | **Risk Score:** 74/100

#### Description
A decentralized game where players submit a secret answer hash first, then reveal it for a reward. Because the reveal transaction is public in the mempool, a bot can copy the revealed answer and front-run the original player with a higher gas price to claim the prize.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract FrontRunnable {

    bytes32 public answerHash;
    address public owner;
    uint256 public reward;

    constructor(bytes32 _answerHash) payable {
        answerHash = _answerHash;
        owner = msg.sender;
        reward = msg.value;
    }

    // VULNERABLE: Anyone watching the mempool can copy _answer
    // from a pending reveal tx and resubmit it with a higher gas price
    function reveal(string calldata _answer) external {
        require(
            keccak256(abi.encodePacked(_answer)) == answerHash,
            "Wrong answer"
        );
        require(reward > 0, "Already claimed");

        reward = 0; // BUG: reward is zeroed before being read below

        // Front-runner intercepts here before original tx mines
        // SECONDARY BUG: reward is already 0 here — winner receives nothing
        (bool ok, ) = msg.sender.call{value: reward}("");
        require(ok, "Transfer failed");
    }

    function updateAnswer(bytes32 _newHash) external {
        require(msg.sender == owner, "Not owner");
        answerHash = _newHash;
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 HIGH, 1 MEDIUM vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Front-Running (Transaction Ordering Dependence) | HIGH | 17–26 | The `reveal()` function exposes the winning answer in plaintext in the mempool. An MEV bot monitors pending transactions, copies the answer, and resubmits with higher gas to be mined first. Also note: `reward` is set to `0` before reading its value, so the transfer always sends 0 ETH — a secondary logic bug. |
| Logic Error (Read After Zero) | MEDIUM | 23–24 | `reward` is set to `0` on line 23, then used in the `.call` on line 24. The winner always receives 0 ETH regardless of the reward balance. |

#### Recommendation
Use a **commit-reveal scheme**: require players to submit a hash of `(answer + salt)` first, then reveal both in a second transaction after a time lock. Use Flashbots Protect RPC or private mempools to prevent MEV exploitation.

---

### Contract 4: Timestamp.sol

<!-- Severity: MEDIUM | Risk Score: 55/100 -->
**Category:** Block Timestamp Manipulation | **Severity:** MEDIUM | **Risk Score:** 55/100

#### Description
A lottery contract that uses `block.timestamp` as the sole source of randomness for picking winners. Miners can manipulate the timestamp within a ~15-second window.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Timestamp {

    address[] public participants;
    address public owner;
    uint256 public ticketPrice = 0.01 ether;

    constructor() { owner = msg.sender; }

    function enter() external payable {
        require(msg.value == ticketPrice, "Wrong ticket price");
        participants.push(msg.sender);
    }

    function pickWinner() external {
        require(msg.sender == owner, "Not owner");
        require(participants.length > 0, "No participants");

        // VULNERABLE: block.timestamp is miner-influenceable within ~15 seconds
        uint256 index = uint256(
            keccak256(abi.encodePacked(block.timestamp))
        ) % participants.length;

        address winner = participants[index];
        (bool ok, ) = winner.call{value: address(this).balance}("");
        require(ok, "Payout failed");
        delete participants;
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 MEDIUM vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Weak Randomness (Timestamp) | MEDIUM | 19–21 | `block.timestamp` used as randomness seed. Miners can shift timestamp by ~15s to influence winner selection. |

#### Recommendation
Use **Chainlink VRF** (Verifiable Random Function) for secure on-chain randomness instead of `block.timestamp` or `block.prevrandao`.

---

### Contract 5: UncheckedCall.sol

<!-- Severity: HIGH | Risk Score: 68/100 -->
**Category:** Unchecked Return Values | **Severity:** HIGH | **Risk Score:** 68/100

#### Description
A payment splitter that distributes ETH to multiple recipients but does not check the return value of low-level `.send()` calls, silently ignoring failed transfers.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PaymentSplitter {

    address[] public payees;
    mapping(address => uint256) public shares;
    uint256 public totalShares;

    function addPayee(address payee, uint256 share) external {
        payees.push(payee);
        shares[payee] = share;
        totalShares += share;
    }

    function distribute() external payable {
        uint256 total = msg.value;
        for (uint i = 0; i < payees.length; i++) {
            uint256 payment = (total * shares[payees[i]]) / totalShares;
            // VULNERABLE: .send() return value is not checked
            // If recipient reverts, ETH is silently lost
            payees[i].send(payment);
        }
    }

    function emergencyWithdraw(address payable to) external {
        // VULNERABLE: .transfer() throws on >2300 gas forwarded
        // but can fail silently for smart contract wallets (e.g. Gnosis Safe)
        to.transfer(address(this).balance);
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 HIGH, 1 LOW vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Unchecked Return Value (`.send`) | HIGH | 19 | Return value of `.send()` is ignored. If a payee is a contract that reverts, the ETH is silently lost. |
| Use of `.transfer()` | LOW | 24 | `.transfer()` forwards only 2300 gas, which can fail for smart contract recipients (e.g., Gnosis Safe). |

#### Recommendation
Replace `.send()` and `.transfer()` with `.call{value:...}('')` and always check the boolean return value.

---

### Contract 6: TxOriginAuth.sol

<!-- Severity: HIGH | Risk Score: 72/100 -->
**Category:** tx.origin Authentication Bypass | **Severity:** HIGH | **Risk Score:** 72/100

#### Description
A simple wallet that uses `tx.origin` for authentication instead of `msg.sender`. This allows a phishing attack where a malicious contract tricks the owner into calling it, then forwards the call to drain the wallet.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TxOriginAuth {

    address public owner;

    constructor() payable {
        owner = msg.sender;
    }

    function transfer(address payable dest, uint256 amount) public {
        // VULNERABLE: tx.origin is always the originating EOA
        // A malicious contract in the call chain can bypass this check
        require(tx.origin == owner, "Not authorized");
        dest.transfer(amount);
    }

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    receive() external payable {}
}
```

#### Expected Scanner Result

> **FAIL — 1 HIGH vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| tx.origin Authentication | HIGH | 12 | `tx.origin` is always the EOA that originated the transaction. A malicious intermediary contract can bypass this check by tricking the owner into calling it. |

#### Recommendation
Replace `tx.origin` with `msg.sender` for authorization checks. Use OpenZeppelin's `Ownable` for robust ownership patterns.

---

### Contract 7: SelfDestructable.sol

<!-- Severity: MEDIUM | Risk Score: 50/100 -->
**Category:** Selfdestruct / Forceful ETH Injection | **Severity:** MEDIUM | **Risk Score:** 50/100

#### Description
A contract whose logic depends on `address(this).balance` for accounting. A `selfdestruct` call from another contract can force ETH into it, breaking internal invariants.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBank {

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
        // A selfdestruct attack can make balance > depositTotal,
        // permanently breaking this invariant
        return address(this).balance;
    }

    function invariantCheck() public view returns (bool) {
        // This invariant CAN be broken by forced ETH injection
        return address(this).balance == depositTotal;
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 MEDIUM vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Reliance on `address(this).balance` | MEDIUM | 27–29 | Contract assumes ETH balance equals tracked deposits. An attacker can forcibly send ETH via `selfdestruct`, permanently breaking the invariant. |

#### Recommendation
Never assume `address(this).balance` equals internal accounting. Track received ETH explicitly and use internal accounting variables for all business logic.

---

### Contract 8: VulnerableProxy.sol

<!-- Severity: CRITICAL | Risk Score: 92/100 -->
**Category:** Delegatecall Storage Collision | **Severity:** CRITICAL | **Risk Score:** 92/100

#### Description
An upgradeable proxy contract using `delegatecall`. The implementation contract's storage layout mismatches the proxy's storage, allowing an attacker to overwrite the `owner` slot by calling a function in the logic contract.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Logic contract — storage slot 0 = 'count', slot 1 = 'owner'
contract LogicV1 {
    uint256 public count; // slot 0
    address public owner; // slot 1

    function increment() public { count++; }
    function setOwner(address _o) public { owner = _o; }
}

// Proxy — storage slot 0 = 'implementation', slot 1 = 'proxyOwner'
contract VulnerableProxy {
    // VULNERABLE: slot 0 collides with LogicV1.count
    address public implementation; // slot 0 ← COLLIDES with LogicV1.count
    // VULNERABLE: slot 1 collides with LogicV1.owner
    address public proxyOwner;     // slot 1 ← COLLIDES with LogicV1.owner

    constructor(address _impl) {
        implementation = _impl;
        proxyOwner = msg.sender;
    }

    fallback() external payable {
        address impl = implementation;
        assembly {
            // VULNERABLE: delegatecall executes logic in proxy's storage context
            // Calling increment() corrupts 'implementation'; setOwner() overwrites 'proxyOwner'
            calldatacopy(0, 0, calldatasize())
            let result := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 CRITICAL vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Delegatecall Storage Collision | CRITICAL | 13–14 | Proxy slot 0 (`implementation` address) collides with `LogicV1` slot 0 (`count`). Calling `increment()` on the proxy corrupts the implementation address. Calling `setOwner()` overwrites `proxyOwner`. |

#### Recommendation
Use **EIP-1967 unstructured storage slots** (keccak256-derived) for implementation and admin addresses to avoid slot collisions.

---

### Contract 9: DOS.sol

<!-- Severity: MEDIUM | Risk Score: 52/100 -->
**Category:** Denial of Service (Gas Griefing) | **Severity:** MEDIUM | **Risk Score:** 52/100

#### Description
A crowdfund contract that iterates over all contributors to issue refunds. An attacker can add thousands of entries to make the `refundAll()` loop too expensive to execute, effectively locking funds.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract DOS {

    address[] public contributors;
    mapping(address => uint256) public contributions;
    uint256 public goal;
    bool public goalReached;

    constructor(uint256 _goal) { goal = _goal; }

    function contribute() external payable {
        if (contributions[msg.sender] == 0) {
            contributors.push(msg.sender); // Attacker can bloat this array cheaply
        }
        contributions[msg.sender] += msg.value;
        if (address(this).balance >= goal) goalReached = true;
    }

    function refundAll() external {
        // VULNERABLE: Unbounded loop — O(n) over contributors array
        // An attacker flooding contribute() can push this past the block gas limit
        require(!goalReached, "Goal was reached");
        for (uint i = 0; i < contributors.length; i++) {
            address payable c = payable(contributors[i]);
            uint256 amount = contributions[c];
            contributions[c] = 0;
            c.transfer(amount); // Also uses deprecated .transfer()
        }
    }
}
```

#### Expected Scanner Result

> **FAIL — 1 MEDIUM, 1 LOW vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Denial of Service (Unbounded Loop) | MEDIUM | 21–27 | `refundAll()` iterates over all contributors. An attacker can flood `contribute()` to make the array too large, causing `refundAll()` to exceed the block gas limit and lock funds permanently. |
| Use of `.transfer()` | LOW | 25 | `.transfer()` with 2300 gas limit can fail for contract recipients. |

#### Recommendation
Use the **pull-payment (withdrawal) pattern**: let each contributor call a `withdraw()` function individually rather than pushing ETH in a loop.

---

### Contract 10: UnsafeProxy.sol

<!-- Severity: CRITICAL | Risk Score: 91/100 -->
**Category:** Uninitialized Storage Pointer / Missing Initializer | **Severity:** CRITICAL | **Risk Score:** 91/100

#### Description
An upgradeable contract that inherits from OpenZeppelin's `Initializable` but forgets to call the initializer. The `owner` variable is never set, leaving it as `address(0)`. Any caller can invoke `initialize()` post-deployment and seize ownership of the contract.

#### Contract Source Code

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Simulated Initializable base (mirrors OpenZeppelin pattern)
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

    // VULNERABLE: initializer is defined but never called during deployment
    // No constructor calls initialize(), so owner stays address(0)
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

    // VULNERABLE: No access control — anyone can call this
    // since owner == address(0), the onlyOwner check is never applied
    function setTreasury(uint256 amount) external {
        treasuryBalance = amount;
    }
}

// Proxy deploys logic but never initializes it
contract UnsafeProxy {

    address public implementation;

    constructor(address _impl) {
        implementation = _impl;
        // MISSING: IVulnerableLogic(_impl).initialize(msg.sender);
        // Without this, owner remains address(0) in the proxy's storage
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
```

#### Expected Scanner Result

> **FAIL — 1 CRITICAL, 1 HIGH vulnerability detected**

| Vulnerability | Severity | Line(s) | Description |
|---|:-:|:-:|---|
| Uninitialized Proxy / Missing Initializer Call | CRITICAL | 44–47 | `UnsafeProxy` constructor deploys the implementation but never calls `initialize()`. `owner` remains `address(0)`, allowing any EOA to call `initialize()` and take full ownership of the contract and its funds. |
| Missing Access Control on `setTreasury()` | HIGH | 36–38 | `setTreasury()` has no access control modifier. Any caller can arbitrarily set `treasuryBalance` to any value, enabling accounting manipulation. |

#### Recommendation
Always call the initializer in the proxy constructor or deployment script. Use OpenZeppelin's **Upgrades Plugin** which automatically checks for uninitialized proxies. Add `onlyOwner` modifiers to all sensitive state-changing functions.

---

## 5. Appendix — Vulnerability Taxonomy

<!-- Maps each vulnerability class covered in this suite to a plain-English description.
     These align with industry-standard identifiers (SWC Registry, Slither detectors, etc.) -->

| Vulnerability | Description |
|---|---|
| **Reentrancy** | External calls made before state updates allow recursive re-entry. |
| **Integer Overflow/Underflow** | Arithmetic wraps silently in Solidity <0.8.0. |
| **Front-Running / TOD** | Transaction ordering exploited by observing mempool and resubmitting with higher gas. |
| **Timestamp Manipulation** | `block.timestamp` is miner-influenceable within ~15 seconds. |
| **Unchecked Return Values** | `.send()`/`.call()` return values ignored silently. |
| **tx.origin Authentication** | Using `tx.origin` instead of `msg.sender` for auth. |
| **Forced ETH via Selfdestruct** | ETH sent via `selfdestruct` bypasses `receive()` hooks. |
| **Delegatecall Storage Collision** | Storage layout mismatch between proxy and implementation. |
| **DoS — Unbounded Loop** | Loops over user-supplied arrays can exceed gas limits. |
| **Uninitialized Proxy** | Upgradeable contracts not calling initializer leave `owner` as `address(0)`. |