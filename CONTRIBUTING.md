# Contributing to BlockScope

Thank you for your interest in contributing to BlockScope.

BlockScope is an academic, production-structured smart contract vulnerability scanner built using FastAPI, React, PostgreSQL, Redis, and Docker.

This repository follows a controlled pull request (PR) workflow.

---

## Contribution Model

- Contributions are PR-based.
- Direct pushes to `main` are not allowed.
- All changes must go through review.
- Forks are not required (internal contributor model).
- Each feature or fix must use a dedicated branch.

---

## Branching Strategy

### Base Branch

- `main` → Stable branch
- All PRs must target `main`

### Branch Naming Convention

| Type | Format | Example |
|------|--------|---------|
| Feature | `feat/<short-description>` | `feat/add-reentrancy-rule` |
| Bug Fix | `fix/<short-description>` | `fix/scan-validation-error` |
| Documentation | `docs/<short-description>` | `docs/update-user-guide` |
| Refactor | `refactor/<short-description>` | `refactor/db-session-handling` |
| Test | `test/<short-description>` | `test/add-scan-endpoint-tests` |

Example:

```bash
git checkout -b feat/add-rate-limit-middleware
```

---

## Development Setup

BlockScope supports two development modes:

### Option 1 – Docker (Recommended for Quick Setup)

```bash
docker compose -f docker/docker-compose.prod.yml up --build
```

Services started:

- Backend (FastAPI)
- Frontend (React)
- PostgreSQL
- Redis
- Nginx reverse proxy

App available at:

```
http://localhost
```

---

### Option 2 – Local Development (Recommended for Active Backend Development)

#### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start PostgreSQL locally.

Run backend:

```bash
uvicorn app.main:app --reload
```

Swagger:

```
http://localhost:8000/docs
```

---

#### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

## Database & Migrations

BlockScope uses:

- PostgreSQL
- SQLAlchemy
- Alembic (if enabled)

If models change:

- Update migration files
- Ensure schema changes are tested
- Never modify production tables directly

---

## Coding Standards

### Backend (Python / FastAPI)

- Follow PEP8
- Use type hints
- Use dependency injection (`Depends`)
- Avoid business logic inside routers
- Keep analysis engine modular
- All endpoints must return structured responses

### Frontend (React / Vite)

- Functional components
- Clear separation of API layer
- Avoid hardcoded URLs (use config)
- Handle API errors gracefully

---

## Commit Message Convention

Use conventional commits:

| Type | Example |
|------|---------|
| feat | `feat: add scan pagination support` |
| fix | `fix: handle empty contract submission` |
| docs | `docs: update API examples` |
| refactor | `refactor: extract db session logic` |
| test | `test: add integration test for scan endpoint` |

---

## Pull Request Requirements

Before opening a PR:

- Code builds successfully
- Backend starts without errors
- Docker setup still works
- No broken imports
- No hardcoded credentials
- Tests pass (if applicable)
- Documentation updated if needed

PR must include:

- Clear description of changes
- Screenshots (if frontend changes)
- Mention if database schema changed
- Mention if breaking changes introduced

---

## What Not To Do

- Do not commit `.env` files
- Do not commit database dumps
- Do not expose secrets
- Do not push directly to `main`
- Do not mix unrelated changes in one PR

---

## Security Notice

BlockScope deals with smart contract analysis and database storage.

All contributors must:

- Avoid introducing unsafe eval/exec patterns
- Validate user input
- Handle database sessions properly
- Avoid logging sensitive data

---

## Review Process

1. Open PR to `main`
2. Reviewer evaluates using `CODE_REVIEW_CHECKLIST.md`
3. Changes requested if needed
4. Approved → merged

---

Thank you for contributing to BlockScope.
