# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of BlockScope seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to: **security@blockscope.io**
3. Include the following in your report:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Assessment**: Within 5 business days
- **Resolution**: Critical issues within 7 days, others within 30 days
- **Credit**: We will credit you in the fix (unless you prefer anonymity)

## Security Best Practices

### Environment Variables

- **NEVER** commit `.env` files with real credentials
- Use `.env.example` as a template — copy and fill in actual values
- Generate secure keys using:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- Rotate secrets regularly, especially after team member departures

### API Keys

- API keys are hashed (SHA-256) before storage — raw keys are shown only once
- Keys support tier-based rate limiting (free, pro, enterprise)
- Revoke compromised keys immediately via the admin API
- Use IP allowlisting for production API keys when possible

### Authentication & Authorization

- JWTs are signed with HS256 and have configurable expiration
- Passwords are hashed using bcrypt with configurable rounds (default: 12)
- API key authentication is available via `X-API-Key` header

### Rate Limiting

- Sliding window rate limiting implemented via Redis
- Default free tier: 100 requests/hour
- Rate limit headers included in all responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

### Security Headers

All responses include OWASP-recommended security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (production only)
- `Content-Security-Policy`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`
- `Cache-Control: no-store` (for API responses)

### Input Validation

- All file uploads validated for size, extension, MIME type, and content
- Input sanitization prevents XSS and injection attacks
- SQL injection prevented via SQLAlchemy ORM parameterized queries
- Path traversal prevention on file operations

### Pre-commit Hooks

The following pre-commit hooks are configured:
- `detect-private-key` — blocks commits containing private keys
- `detect-secrets` — scans for hardcoded secrets and credentials
- `bandit` — Python security linter
- `check-added-large-files` — prevents accidental large file commits

To install:
```bash
pip install pre-commit
pre-commit install
```

### Development vs Production

| Setting              | Development          | Production           |
| -------------------- | -------------------- | -------------------- |
| DEBUG                | `True`               | `False`              |
| Rate Limiting        | Disabled             | Enabled (strict)     |
| CORS                 | Permissive           | Restrictive          |
| API Docs             | Enabled              | Disabled             |
| Log Response Bodies  | Yes                  | Never                |
| SQL Logging          | Enabled              | Disabled             |
| HTTPS                | Optional             | Required             |
| Secret Key Length    | 64+ chars            | 64+ chars            |

## Dependency Security

- Dependencies are pinned in `requirements.txt` for reproducibility
- Run `safety check` regularly to scan for known vulnerabilities
- Run `bandit -r backend/app/` for Python security analysis
- Keep dependencies updated: `pip list --outdated`

## Infrastructure Security

### Database
- Use strong, unique passwords for all database accounts
- Enable SSL connections in production
- Limit database user permissions to only what's needed
- Enable connection pooling with `pool_pre_ping=True`

### Redis
- Use password authentication in production
- Bind to localhost or use SSL for remote connections
- Set `maxmemory` limits to prevent OOM

### Docker
- Use non-root users in containers
- Scan images for vulnerabilities
- Keep base images updated
- Use multi-stage builds to minimize attack surface

## Changelog

| Date       | Change                                      |
| ---------- | ------------------------------------------- |
| 2026-03-03 | Initial security policy and hardening |
