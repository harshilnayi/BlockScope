# BlockScope – Code Review Checklist

This checklist is used by reviewers before approving any pull request.

All pull requests must pass these checks before merge into `main`.

---

# 1. General Quality

- [ ] PR has a clear and descriptive title
- [ ] PR description explains *what* and *why*
- [ ] Changes are scoped (no unrelated modifications)
- [ ] No unnecessary files committed
- [ ] No merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)

---

# 2. Backend (FastAPI / Python)

## Structure & Design

- [ ] Business logic is not placed directly inside routers
- [ ] Dependency injection (`Depends`) used correctly
- [ ] No duplicated logic
- [ ] Functions are reasonably sized and readable
- [ ] Type hints are present

## Validation & Error Handling

- [ ] Input validation handled properly
- [ ] Proper HTTP status codes used (400, 404, 500, etc.)
- [ ] Exceptions are handled safely
- [ ] No internal stack traces leaked to client

## Security

- [ ] No hardcoded secrets
- [ ] No unsafe `eval`, `exec`, or dynamic imports
- [ ] User input is validated before DB interaction
- [ ] Sensitive data not logged
- [ ] CORS configuration not overly permissive in production

## Database & Migrations

- [ ] Model changes reviewed carefully
- [ ] Migration required? If yes, migration included
- [ ] No destructive schema changes without discussion
- [ ] Queries are efficient (no N+1 patterns)
- [ ] Sessions are properly committed/closed

---

# 3. Frontend (React / Vite)

## Structure

- [ ] Functional components used
- [ ] No duplicated logic
- [ ] Clean separation between UI and API calls

## API Handling

- [ ] Proper error handling
- [ ] No hardcoded backend URLs
- [ ] Loading states handled properly
- [ ] Response parsing matches backend schema

## UI & UX

- [ ] No obvious console errors
- [ ] No broken layout
- [ ] Clear user feedback on scan results

---

# 4. Docker & Infrastructure

- [ ] Docker build succeeds
- [ ] docker-compose works correctly
- [ ] No unnecessary exposed ports
- [ ] Environment variables not hardcoded
- [ ] .env files not committed
- [ ] Health checks still functional

---

# 5. Performance Considerations

- [ ] No blocking I/O inside async routes
- [ ] No unnecessary heavy computation in request cycle
- [ ] Large payload handling validated
- [ ] No inefficient database loops

---

# 6. Testing

- [ ] Existing tests still pass
- [ ] New feature includes tests (if applicable)
- [ ] No test failures in CI
- [ ] Edge cases considered

---

# 7. Documentation

- [ ] Documentation updated if API changed
- [ ] README updated if setup changed
- [ ] Examples updated if response schema changed
- [ ] Swagger still reflects correct schema

---

# 8. Breaking Changes

If the PR introduces breaking changes:

- [ ] Clearly documented in PR
- [ ] Database impact described
- [ ] API contract changes explained
- [ ] Frontend compatibility verified

---

# 9. Final Verification Before Merge

- [ ] Project runs locally
- [ ] Docker stack runs successfully
- [ ] Scan endpoint works
- [ ] Health endpoint returns healthy
- [ ] No debug logs left in production code

---

## Reviewer Decision

- [ ] Approve
- [ ] Request changes
- [ ] Reject

---

This checklist must be reviewed before merging any pull request into `main`.
