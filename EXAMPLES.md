# BlockScope – Example Usage

This document provides real API examples using the BlockScope backend.

All examples below were generated using a running local instance of the API.

Base URL (local development):

```
http://localhost:8000
```

---

## Example 1 – Scanning a Safe Contract

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "SafeCounter",
  "source_code": "pragma solidity ^0.8.0; contract SafeCounter { uint public count; function increment() public { count += 1; } }"
}
```

---

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

This indicates that the contract passed all configured analysis checks.

---

## Example 2 – Scanning Another Contract

### Request

**POST** `/api/v1/scan`

```json
{
  "contract_name": "ReentrancyTest",
  "source_code": "pragma solidity ^0.8.0; contract ReentrancyTest { mapping(address => uint) public balances; function withdraw() public { uint amount = balances[msg.sender]; (bool success,) = msg.sender.call{value: amount}(\"\"); require(success); balances[msg.sender] = 0; } }"
}
```

---

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

> Note: Vulnerability detection depends on the active rule set configured in the `AnalysisOrchestrator`. If no rules are loaded, contracts will return as SAFE.

---

## Example 3 – List Recent Scans

### Request

**GET** `/api/v1/scans?skip=0&limit=10`

---

### Response

```json
[
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
]
```

---

## Example 4 – Get a Specific Scan

### Request

**GET** `/api/v1/scans/1`

---

### Response

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

## Example 5 – Health Check

### Request

**GET** `/health`

---

### Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "app": "BlockScope API"
}
```

---

## Notes

- Maximum contract size: 200,000 characters
- Empty contracts return HTTP 400
- Large contracts return HTTP 413
- Results are stored in PostgreSQL
- Rule-based analysis depends on configured engine rules
