# BlockScope – Frequently Asked Questions (FAQ)

This document answers common questions about installing, running, and using BlockScope.

---

## 1. What is BlockScope?

BlockScope is a Smart Contract Vulnerability Scanner built with FastAPI (backend) and React (frontend).  
It analyzes Solidity contract source code and returns structured vulnerability findings, along with a severity breakdown and overall security score.

---

## 2. What smart contract languages are supported?

Currently, BlockScope is designed for **Solidity contracts**.  
The API expects Solidity source code as raw text inside a JSON request.

---

## 3. How do I scan a contract?

Send a POST request to:

```
POST /api/v1/scan
```

Example request body:

```json
{
  "contract_name": "MyToken",
  "source_code": "pragma solidity ^0.8.0; contract MyToken { ... }"
}
```

The frontend automatically sends requests in this format when you paste contract code.

---

## 4. What happens when I submit a scan?

When you submit a contract:

1. The request is validated.
2. The contract size is checked.
3. The AnalysisOrchestrator runs vulnerability analysis.
4. Results are stored in the database.
5. Structured findings are returned in the response.

---

## 5. What is the maximum contract size?

BlockScope limits contract size to:

**200,000 characters**

If exceeded, the API returns:

```
HTTP 413 – Contract code too large
```

---

## 6. What happens if I submit an empty contract?

If `source_code` is empty or only whitespace, the API returns:

```
HTTP 400 – Contract code cannot be empty
```

---

## 7. Does BlockScope store my contract?

Yes.  
Each scan is stored in PostgreSQL with:

- Contract name
- Source code
- Vulnerability count
- Severity breakdown
- Overall score
- Summary
- Findings
- Timestamp

---

## 8. How can I retrieve past scans?

You can use:

```
GET /api/v1/scans
```

Supports pagination:

```
GET /api/v1/scans?skip=0&limit=10
```

- `skip` = number of records to skip
- `limit` = number of records to return

---

## 9. How do I retrieve a specific scan?

Use:

```
GET /api/v1/scans/{scan_id}
```

If the scan does not exist:

```
HTTP 404 – Scan {id} not found
```

---

## 10. What does the scan response include?

Each scan response includes:

- `scan_id`
- `contract_name`
- `vulnerabilities_count`
- `severity_breakdown`
- `overall_score`
- `summary`
- `findings`
- `timestamp`

Each finding contains:

- `rule_id`
- `name`
- `severity`
- `description`
- `line_number`
- `code_snippet`
- `remediation`
- `confidence`

---

## 11. What severities are supported?

Findings may include:

- CRITICAL
- HIGH
- MEDIUM
- LOW

---

## 12. What database does BlockScope use?

BlockScope uses:

- **PostgreSQL** for persistent storage
- **SQLAlchemy ORM**
- **Alembic** for migrations

The database connection is configured using:

```
DATABASE_URL
```

---

## 13. Does BlockScope require Redis?

Redis is configured in settings but is not required for basic scanning functionality.  
It may be used for:

- Rate limiting
- Caching
- Future scalability features

---

## 14. Is authentication required?

Currently, the scan endpoint does not enforce authentication by default.  
Security-related settings such as:

- `SECRET_KEY`
- JWT configuration
- Token expiry

exist for future expansion.

---

## 15. How do I check if the API is healthy?

Use:

```
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "version": "0.1.0"
  "app": "BlockScope API"
}
```

If the database is disconnected, status may return as `"degraded"`.

---

## 16. Why am I getting a 500 error?

A 500 error usually indicates:

- Analysis failure
- Database connection issue
- Unexpected runtime exception

Check backend logs for detailed error information.

---

## 17. Why am I getting a 404 error?

Possible reasons:

- Invalid endpoint
- Incorrect API prefix
- Scan ID does not exist

Correct API prefix:

```
/api/v1
```

---

## 18. Does BlockScope support file uploads?

Currently, the API expects raw source code as text inside JSON.  
File upload functionality is not implemented yet.

---

## 19. Can BlockScope run in production?

Yes.  
Production setup includes:

- Multi-stage Docker builds
- Nginx reverse proxy
- PostgreSQL
- Redis (optional)
- Deployment scripts
- Health checks

Refer to `USER_GUIDE.md` for production deployment steps.

---

## 20. How is vulnerability scoring calculated?

The following values are computed by the analysis engine:

- `vulnerabilities_count`
- `severity_breakdown`
- `overall_score`

The scoring logic is implemented inside the AnalysisOrchestrator.

---

## 21. Can I disable database persistence?

Currently, database persistence is part of the scan flow.  
Each scan is automatically stored when processed.

---

## 22. How can I configure environment variables?

BlockScope uses a `.env` file.  
Important environment variables include:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`

Settings are loaded using Pydantic BaseSettings.

---

## 23. Does BlockScope expose Swagger documentation?

Yes.  
If enabled, documentation is available at:

```
/docs
```

This may be disabled in production environments.

---

# Still have questions?

Open an issue in the repository or contact the maintainers.
