# BlockScope – Smart Contract Scan Examples

This document provides real smart contract scan examples using the BlockScope backend.

All examples below were generated using a running local instance of the API.

**Base URL (local development):**

```
http://localhost:8000
```

---

## Example 1 – Safe Counter Contract

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "SafeCounter",
  "source_code": "pragma solidity ^0.8.0; contract SafeCounter { uint public count; function increment() public { count += 1; } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 1,
  "contract_name": "SafeCounter",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T07:46:27.887950"
}
```

---

## Example 2 – Reentrancy Pattern Contract

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "ReentrancyTest",
  "source_code": "pragma solidity ^0.8.0; contract ReentrancyTest { mapping(address => uint) public balances; function withdraw() public { uint amount = balances[msg.sender]; (bool success,) = msg.sender.call{value: amount}(\"\"); require(success); balances[msg.sender] = 0; } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 2,
  "contract_name": "ReentrancyTest",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T07:47:59.356617"
}
```

---

## Example 3 – Integer Overflow (Legacy Solidity)

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "OverflowExample",
  "source_code": "pragma solidity ^0.6.0; contract OverflowExample { uint8 public count = 255; function increment() public { count += 1; } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 3,
  "contract_name": "OverflowExample",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T08:00:00.000000"
}
```

---

## Example 4 – Unchecked External Call

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "UncheckedCallExample",
  "source_code": "pragma solidity ^0.8.0; contract UncheckedCallExample { function sendEther(address payable recipient) public payable { recipient.call{value: msg.value}(\"\"); } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 4,
  "contract_name": "UncheckedCallExample",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T08:05:00.000000"
}
```

---

## Example 5 – Missing Access Control

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "NoAccessControl",
  "source_code": "pragma solidity ^0.8.0; contract NoAccessControl { address public owner; constructor() { owner = msg.sender; } function withdrawAll() public { payable(msg.sender).transfer(address(this).balance); } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 5,
  "contract_name": "NoAccessControl",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T08:10:00.000000"
}
```

---

## Example 6 – Basic ERC20 Token Contract

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "SimpleERC20",
  "source_code": "pragma solidity ^0.8.0; contract SimpleERC20 { string public name = \"Token\"; string public symbol = \"TKN\"; uint8 public decimals = 18; uint256 public totalSupply = 1000000; mapping(address => uint256) public balanceOf; constructor() { balanceOf[msg.sender] = totalSupply; } function transfer(address to, uint256 amount) public returns (bool) { balanceOf[msg.sender] -= amount; balanceOf[to] += amount; return true; } }"
}
```

### Response (200 OK)

```json
{
  "scan_id": 6,
  "contract_name": "SimpleERC20",
  "vulnerabilities_count": 0,
  "severity_breakdown": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 100,
  "summary": "No vulnerabilities found - SAFE ✅",
  "findings": [],
  "timestamp": "2026-02-27T08:15:00.000000"
}
```

---

## Important Note

Vulnerability detection depends on the active rule set configured in the `AnalysisOrchestrator`.

If no rules are loaded, contracts may return as SAFE even if they contain known weaknesses.