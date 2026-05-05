# BlockScope — Vulnerability Assessment Report

**Project:** BlockScope (Solidity Smart Contract Security Scanner)
**Assessment Date:** 2026-05-05
**Prepared By:** Security Testing Suite (PR #44)
**Scope:** Backend REST API (`/api/v1/*`), file-upload pipeline, authentication layer, database layer

---

## Executive Summary

The security test suite (`tests/test_security.py`) performed an automated vulnerability assessment
covering five attack surface categories: SQL Injection, Cross-Site Scripting (XSS), CSRF
protection, Authentication Bypass, and File Upload abuse. A supporting edge-case suite
(`tests/test_edge_cases.py`) exercised boundary values, concurrent access patterns, and database
failure modes.

| Severity | Count | Status |
|----------|------:|-------|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 3 | See below |
| Low | 4 | See below |
| Informational | 2 | See below |

---

## Findings

### VULN-001 — SQL Injection via `contract_name` field
**Severity:** Medium
**CWE:** CWE-89 (SQL Injection)
**Test:** `TestSQLInjection::test_sql_injection_in_contract_name`

**Description:**
The `/api/v1/scan` endpoint accepts a user-controlled `contract_name` string that is persisted to
the database. Ten canonical SQL injection payloads (UNION-based, stacked queries, sleep-based blind
injection) were submitted. The ORM layer (SQLAlchemy) correctly parameterises all queries, so
injection was not possible. However, the raw error message path was checked — if the ORM is ever
bypassed with raw SQL, these payloads would be dangerous.

**Reproduction:**
```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"source_code": "...", "contract_name": "\"; DROP TABLE scans; --"}'
```

**Impact:** If the ORM layer were removed or bypassed, an attacker could read, modify, or delete
all scan records in the database.

**Remediation:** ✅ Mitigated by SQLAlchemy ORM parameterisation. Ensure no raw `execute()` calls
are ever added without explicit parameter binding. Add a CI lint rule (e.g. `bandit B608`) to
detect raw SQL string interpolation.

---

### VULN-002 — Missing HTTP Security Headers
**Severity:** Medium
**CWE:** CWE-693 (Protection Mechanism Failure)
**Test:** `TestXSSProtection::test_security_headers_present_on_all_responses`

**Description:**
The API responses were checked for `X-Content-Type-Options` and `X-Frame-Options` headers. If
either is absent, browsers may sniff MIME types or embed API responses in iframes, enabling
clickjacking or MIME-confusion attacks.

**Impact:** Without `X-Frame-Options: DENY`, an attacker can embed the API response inside a hidden
iframe and trigger actions on behalf of an authenticated user (UI redressing / clickjacking).

**Remediation:** Add a global response middleware that injects the following headers on every
response:
```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
```

---

### VULN-003 — File Upload Extension Bypass (Double Extension)
**Severity:** Medium
**CWE:** CWE-434 (Unrestricted Upload of File with Dangerous Type)
**Test:** `TestFileUploadSecurity::test_double_extension_rejected`

**Description:**
Files named `evil.exe.sol` pass the extension check because only the final extension (`.sol`) is
validated. An attacker could upload a file with a double extension whose first component is a
dangerous type (`.php`, `.sh`, `.exe`), and if the file is ever served back or executed, the
intermediate extension may be interpreted by the web server or OS.

**Impact:** Low in the current architecture (uploaded files are read as text and not served
statically), but a high-risk pattern if the storage or serving strategy changes.

**Remediation:** Validate that the filename contains **no** dangerous intermediate extensions:
```python
import re
DANGEROUS_EXT = re.compile(r'\.(php|exe|sh|py|js|html|bat|cmd)', re.IGNORECASE)
if DANGEROUS_EXT.search(Path(filename).stem):
    raise HTTPException(status_code=400, detail="Filename contains a disallowed extension segment")
```

---

### VULN-004 — Path Traversal in Upload Filename (Informational)
**Severity:** Low
**CWE:** CWE-22 (Path Traversal)
**Test:** `TestFileUploadSecurity::test_path_traversal_in_filename_rejected`

**Description:**
Filenames containing `../`, `/etc/`, or Windows-style `..\\` sequences were submitted. The current
implementation does not appear to store files by filename, so traversal is not exploitable.
However, the `contract_name` stored in the DB may include the traversal string if not sanitised,
which could mislead downstream tooling.

**Remediation:** Strip all directory components from uploaded filenames before storing:
```python
from pathlib import PurePosixPath
safe_name = PurePosixPath(filename).name  # drops any directory prefix
```

---

### VULN-005 — CORS Wildcard Potential in Non-Production Modes
**Severity:** Low
**CWE:** CWE-942 (Overly Permissive Cross-domain Whitelist)
**Test:** `TestCSRFProtection::test_cors_origin_not_wildcard_in_production_mode`

**Description:**
In `DEBUG=True` mode, CORS may be configured with a wildcard `*` origin, allowing any website to
make credentialed cross-origin requests. This was observed to be properly restricted in production
mode (`DEBUG=False`), but the test confirms the guard is in place.

**Remediation:** Ensure the allowed-origins list is loaded from an environment variable and never
defaults to `["*"]` in non-development configurations.

---

### VULN-006 — Server Version Disclosure (Low)
**Severity:** Low
**CWE:** CWE-200 (Exposure of Sensitive Information)
**Test:** `TestSecurityHeadersAndDisclosure::test_server_header_not_exposed`

**Description:**
The `Server` response header may reveal the underlying ASGI server version (e.g. `uvicorn/0.x.x`).
This aids attackers in selecting version-specific exploits.

**Remediation:** Override the `Server` header in the response middleware:
```python
response.headers["Server"] = "BlockScope"
```

---

### VULN-007 — Rate-Limit Bypass via X-Forwarded-For Spoofing (Informational)
**Severity:** Informational
**CWE:** CWE-799 (Improper Control of Interaction Frequency)
**Test:** `TestAuthenticationBypass::test_rate_limit_not_bypassable_via_header_spoofing`

**Description:**
If the rate limiter uses `X-Forwarded-For` as the client identifier without validating against
trusted proxies, an attacker can rotate this header to bypass per-IP rate limits. In the current
test environment (`RATE_LIMIT_ENABLED=False`), this was not directly verifiable.

**Remediation:** Configure the rate limiter to only trust `X-Forwarded-For` from known reverse
proxies (e.g. via `trusted_hosts` middleware), and fall back to the connection remote address.

---

## Methodology

| Phase | Technique | Tools |
|-------|-----------|-------|
| SQL Injection | Parameterised payload injection, DB state verification | pytest, SQLAlchemy |
| XSS | Reflected payload detection, header enumeration | pytest, httpx |
| CSRF | Origin header manipulation, pre-flight analysis | pytest, httpx |
| Auth Bypass | Invalid/malformed key submission, revoked key replay | pytest, custom fixtures |
| File Upload | Extension abuse, path traversal, binary content, encoding attacks | pytest, io.BytesIO |
| Edge Cases | Boundary values, concurrent load, DB failure injection | pytest, threading, MagicMock |

---

## Test Coverage Summary

| Test Class | Tests | Pass Condition |
|---|---|---|
| `TestSQLInjection` | 5 | No DB errors, no data leakage |
| `TestXSSProtection` | 5 | No raw script reflection, headers present |
| `TestCSRFProtection` | 5 | Origin restriction, content-type enforcement |
| `TestAuthenticationBypass` | 7 | No 500s, no elevated access |
| `TestFileUploadSecurity` | 8 | Extension/traversal/encoding rejection |
| `TestSecurityHeadersAndDisclosure` | 5 | No stack traces, no version disclosure |

**Total security tests:** 35
**Total edge-case tests:** 40+

---

## Remediation Priority

| # | Finding | Priority | Effort |
|---|---------|----------|--------|
| 1 | Add global security-header middleware | P1 | Low (< 1h) |
| 2 | Validate double-extension filenames | P1 | Low (< 1h) |
| 3 | Strip directory components from filenames | P2 | Low (< 30m) |
| 4 | Lock CORS origins via environment variable | P1 | Low (< 1h) |
| 5 | Override `Server` response header | P3 | Very low (< 15m) |
| 6 | Harden rate limiter proxy trust | P2 | Medium (2–4h) |
| 7 | Add `bandit` B608 to CI | P2 | Low (< 30m) |

---

*This report was generated from automated test results. Manual penetration testing of the
production deployment is recommended before any public launch.*
