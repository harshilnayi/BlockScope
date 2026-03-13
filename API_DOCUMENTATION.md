# BlockScope — API Documentation

> Complete endpoint reference for the BlockScope Smart Contract Vulnerability Scanner API

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`
**Interactive Docs:** [`/docs`](http://localhost:8000/docs) (Swagger) | [`/redoc`](http://localhost:8000/redoc) (ReDoc)

---

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Scan Endpoints](#scan-endpoints)
  - [POST /api/v1/scan](#post-apiv1scan)
  - [POST /api/v1/scan/file](#post-apiv1scanfile)
  - [GET /api/v1/scans](#get-apiv1scans)
  - [GET /api/v1/scans/:id](#get-apiv1scansid)
  - [DELETE /api/v1/scans/:id](#delete-apiv1scansid)
- [System Endpoints](#system-endpoints)
  - [GET /health](#get-health)
  - [GET /](#get-)
  - [GET /api/v1/info](#get-apiv1info)
- [Error Responses](#error-responses)
- [Data Types](#data-types)

---

## Authentication

BlockScope uses **API Key** authentication via HTTP header. Authentication is **optional** for most endpoints but provides higher rate limits.

| Header | Value |
|--------|-------|
| `X-API-Key` | Your API key (e.g., `bsc_a1b2c3d4e5f6...`) |

### Tiers & Rate Limits

| Tier | Per Minute | Per Hour | Per Day |
|------|-----------|---------|--------|
| **Unauthenticated** | 20 | 100 | 1,000 |
| **Free** | 30 | 200 | 2,000 |
| **Basic** | 60 | 500 | 5,000 |
| **Premium** | 120 | 1,000 | 10,000 |
| **Enterprise** | 300 | 5,000 | 50,000 |

---

## Rate Limiting

When rate limited, the API responds with `429 Too Many Requests`. Rate limit headers are included on every response:

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests for the current window |
| `X-RateLimit-Remaining` | Remaining requests in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the window resets |

---

## Scan Endpoints

### POST `/api/v1/scan`

Scan Solidity source code for vulnerabilities.

**Rate limit:** 5/min, 20/hour (unauthenticated)

#### Request

```http
POST /api/v1/scan HTTP/1.1
Content-Type: application/json
X-API-Key: bsc_your_api_key  (optional)
```

```json
{
  "source_code": "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract MyToken {\n    mapping(address => uint256) public balances;\n\n    function withdraw(uint256 amount) public {\n        require(balances[msg.sender] >= amount);\n        (bool success, ) = msg.sender.call{value: amount}(\"\");\n        require(success);\n        balances[msg.sender] -= amount;\n    }\n}",
  "contract_name": "MyToken"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_code` | string | ✅ | Solidity source code (10–500,000 chars) |
| `contract_name` | string | ❌ | Contract name (auto-detected if omitted) |

#### Response `200 OK`

```json
{
  "scan_id": 42,
  "contract_name": "MyToken",
  "vulnerabilities_count": 1,
  "severity_breakdown": {
    "critical": 1,
    "high": 0,
    "medium": 0,
    "low": 0,
    "info": 0
  },
  "overall_score": 90,
  "summary": "1 critical - NEEDS ATTENTION",
  "findings": [
    {
      "title": "Reentrancy Vulnerability",
      "description": "State change after external call allows reentrancy attack",
      "severity": "critical",
      "line_number": 9
    }
  ],
  "timestamp": "2026-03-04T15:30:00.000Z"
}
```

#### Errors

| Code | Cause |
|------|-------|
| `400` | Source code too short (< 10 chars) or too large (> 500 KB) |
| `429` | Rate limit exceeded |
| `500` | Analysis engine failure |

---

### POST `/api/v1/scan/file`

Upload a `.sol` file for vulnerability scanning.

**Rate limit:** 5/min, 20/hour (unauthenticated)

#### Request

```http
POST /api/v1/scan/file HTTP/1.1
Content-Type: multipart/form-data
X-API-Key: bsc_your_api_key  (optional)
```

```bash
curl -X POST http://localhost:8000/api/v1/scan/file \
  -H "X-API-Key: bsc_your_api_key" \
  -F "file=@MyToken.sol"
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `file` | file | ✅ | `.sol` extension, UTF-8, max 5 MB |

#### Response `200 OK`

Same response format as [POST /api/v1/scan](#post-apiv1scan).

#### File Validation (when security is enabled)

The uploaded file is checked for:
- **Size**: max 5 MB (`MAX_UPLOAD_SIZE`)
- **Extension**: must be `.sol` (`ALLOWED_EXTENSIONS`)
- **MIME type**: must be text-based
- **Content**: scanned for malicious patterns

#### Errors

| Code | Cause |
|------|-------|
| `400` | Invalid file (wrong extension, not UTF-8, too large, malicious content) |
| `429` | Rate limit exceeded |
| `500` | Analysis engine failure |

---

### GET `/api/v1/scans`

List all scans with pagination, ordered by most recent first.

#### Request

```http
GET /api/v1/scans?skip=0&limit=10 HTTP/1.1
X-API-Key: bsc_your_api_key  (optional)
```

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `skip` | int | `0` | ≥ 0 | Number of records to skip |
| `limit` | int | `10` | 1–100 | Number of records to return |

#### Response `200 OK`

```json
[
  {
    "scan_id": 42,
    "contract_name": "MyToken",
    "vulnerabilities_count": 1,
    "severity_breakdown": { "critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0 },
    "overall_score": 90,
    "summary": "1 critical - NEEDS ATTENTION",
    "findings": [...],
    "timestamp": "2026-03-04T15:30:00.000Z"
  }
]
```

#### Errors

| Code | Cause |
|------|-------|
| `400` | `limit` exceeds 100 |
| `500` | Database query failure |

---

### GET `/api/v1/scans/:id`

Get a specific scan by ID with full details.

#### Request

```http
GET /api/v1/scans/42 HTTP/1.1
X-API-Key: bsc_your_api_key  (optional)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scan_id` | int | ✅ | Scan ID (path parameter, ≥ 1) |

#### Response `200 OK`

Same format as individual items in the [list response](#get-apiv1scans).

#### Errors

| Code | Cause |
|------|-------|
| `400` | Invalid scan ID (< 1) |
| `404` | Scan not found |
| `500` | Database query failure |

---

### DELETE `/api/v1/scans/:id`

Delete a scan by ID. **Requires API key authentication.**

> **Note:** This endpoint is only available when security modules are enabled.

#### Request

```http
DELETE /api/v1/scans/42 HTTP/1.1
X-API-Key: bsc_your_api_key  (required)
```

#### Response `200 OK`

```json
{
  "message": "Scan 42 deleted successfully"
}
```

#### Errors

| Code | Cause |
|------|-------|
| `401` | Missing or invalid API key |
| `404` | Scan not found |
| `500` | Database deletion failure |

---

## System Endpoints

### GET `/health`

Health check endpoint for monitoring and load balancers.

#### Response `200 OK`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "app": "BlockScope",
  "database": "connected",
  "redis": "connected"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `status` | `healthy`, `degraded` | Overall system status |
| `database` | `connected`, `disconnected` | PostgreSQL connection state |
| `redis` | `connected`, `disconnected` | Redis connection state (when rate limiting enabled) |

---

### GET `/`

Root endpoint with API welcome message and navigation links.

#### Response `200 OK`

```json
{
  "message": "Welcome to BlockScope",
  "version": "1.0.0",
  "description": "Smart Contract Vulnerability Scanner",
  "docs": "/docs",
  "health": "/health",
  "endpoints": {
    "scan": "/api/v1/scan"
  },
  "security": {
    "enabled": true,
    "rate_limiting": true,
    "authentication": "API Key (optional)"
  }
}
```

---

### GET `/api/v1/info`

Detailed API configuration and capabilities.

#### Response `200 OK`

```json
{
  "name": "BlockScope",
  "version": "1.0.0",
  "environment": "development",
  "debug": true,
  "security": {
    "rate_limiting": true,
    "cors_configured": true,
    "api_key_authentication": true
  },
  "limits": {
    "max_upload_size": "5.0MB",
    "allowed_extensions": [".sol"]
  }
}
```

---

## Error Responses

All errors follow a consistent JSON structure:

```json
{
  "detail": "Human-readable error message"
}
```

### Common Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `400` | Bad Request | Invalid input, missing fields, file too large |
| `401` | Unauthorized | Missing or invalid API key (for protected endpoints) |
| `404` | Not Found | Scan ID doesn't exist |
| `413` | Payload Too Large | Request body exceeds server limits |
| `422` | Validation Error | Request body doesn't match schema |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |

### Validation Error (422) Format

FastAPI returns structured validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "source_code"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Data Types

### ScanResponse

| Field | Type | Description |
|-------|------|-------------|
| `scan_id` | integer | Unique scan identifier |
| `contract_name` | string | Name of the scanned contract |
| `vulnerabilities_count` | integer | Total findings count |
| `severity_breakdown` | object | `{critical, high, medium, low, info}` counts |
| `overall_score` | integer | Security score 0–100 (100 = safest) |
| `summary` | string | One-line human-readable summary |
| `findings` | array | List of `FindingResponse` objects |
| `timestamp` | datetime | ISO 8601 UTC scan timestamp |

### FindingResponse

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Vulnerability title |
| `description` | string | Detailed vulnerability description |
| `severity` | string | `critical`, `high`, `medium`, `low`, or `info` |
| `line_number` | integer \| null | Source code line number (if available) |

### ScanRequest

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_code` | string | ✅ | Solidity source code |
| `contract_name` | string | ❌ | Contract name (auto-detected if not provided) |
