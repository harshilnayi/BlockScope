# BlockScope

[![Backend CI](https://github.com/harshilnayi/BlockScope/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/harshilnayi/BlockScope/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/frontend-ci.yml)
[![Docker Build](https://github.com/harshilnayi/BlockScope/actions/workflows/docker-build.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/docker-build.yml)
[![codecov](https://codecov.io/gh/harshilnayi/BlockScope/branch/main/graph/badge.svg)](https://codecov.io/gh/harshilnayi/BlockScope)

BlockScope is a full-stack smart contract vulnerability scanner for Solidity projects. It combines Slither-based static analysis with custom source-rule detection, stores scan history, exposes a documented FastAPI backend, and provides a React frontend for interactive use.

This README is the practical source of truth for what the project is, how it works, and how to run it in its current working state.

## What BlockScope Does

- Scans Solidity smart contracts for vulnerabilities
- Accepts pasted source code or uploaded `.sol` files
- Produces findings with severity, description, and line references when available
- Calculates an overall security score and severity breakdown
- Stores scan history in PostgreSQL
- Uses Redis for rate limiting and backend caching
- Exposes a browser UI and a documented API

## Current Working State

As of the current repo state:

- Frontend runs on `http://localhost:5173`
- Backend runs on `http://localhost:8000`
- Swagger docs work at `http://localhost:8000/docs`
- Health endpoint works at `http://localhost:8000/health`
- Redis is enabled and reports `ok`
- Docker Compose brings up the full stack
- Backend tests pass
- Frontend build and tests pass

## Main Features

- Dual analysis engine:
  - Slither static analysis
  - Custom source-based fallback rules
- Security scoring:
  - severity breakdown
  - overall score from `0` to `100`
- Developer-friendly UI:
  - upload area
  - paste-in editor
  - scan history
  - result filtering and export helpers
- API surface:
  - scan by JSON
  - scan by file upload
  - list previous scans
  - fetch a scan by ID
- Operational support:
  - health endpoints
  - Swagger docs
  - Dockerized dev stack
  - GitHub Actions CI

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, TailwindCSS |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Analysis | Slither, custom source rules |
| Database | PostgreSQL 15 |
| Cache / Rate Limiting | Redis 7 |
| Containers | Docker, Docker Compose |
| Testing | Pytest, Vitest |

## Architecture

At a high level:

1. The frontend sends contract source code or uploaded Solidity files to the backend.
2. The backend validates the request and runs the analysis pipeline.
3. The analysis pipeline uses Slither and custom rules to generate findings.
4. The backend calculates summary data and persists scans to PostgreSQL.
5. Redis supports rate limiting and caching.
6. Results are returned to the frontend and can also be inspected through the API.

For more detail, see:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)

## Project Structure

```text
BlockScope/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── models/
│   │   ├── routers/
│   │   └── schemas/
│   ├── analysis/
│   ├── cli/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── docker/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
└── README.md
```

## Prerequisites

For the recommended setup:

- Docker Desktop
- Git

For local non-Docker development:

- Python 3.11
- Node.js 20+
- npm

## Quick Start

If you just want the project running with the least friction, use Docker.

```bash
git clone https://github.com/harshilnayi/BlockScope.git
cd BlockScope
docker compose up -d --build
```

Then open:

- Frontend: `http://localhost:5173`
- Backend root: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`

Expected health response:

```json
{"status":"healthy","version":"1.0.0","database":"ok","redis":"ok"}
```

## Recommended Run Method

Use Docker Compose from the repo root.

From `E:\BlockScope` on Windows:

```powershell
docker compose up -d --build
```

Check container status:

```powershell
docker compose ps
```

You should see:

- `blockscope_db`
- `blockscope_redis`
- `blockscope_backend`
- `blockscope_frontend`

## Full Run Guide

### 1. Start the project

```powershell
docker compose up -d --build
```

### 2. Verify the backend

```powershell
curl http://localhost:8000/health
```

Expected:

```json
{"status":"healthy","version":"1.0.0","database":"ok","redis":"ok"}
```

### 3. Verify the frontend

Open:

```text
http://localhost:5173
```

If you still see an older cached UI, do a hard refresh:

```text
Ctrl + Shift + R
```

### 4. Verify the API docs

Open:

```text
http://localhost:8000/docs
```

### 5. Run a scan

You can use either:

- the frontend UI
- Swagger docs
- a direct API request

Example API request:

```bash
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d "{\"source_code\":\"pragma solidity ^0.8.20; contract Test { function ping() public pure returns (uint256) { return 1; } }\",\"contract_name\":\"Test\"}"
```

## Docker Commands You’ll Actually Use

Start everything:

```powershell
docker compose up -d --build
```

See status:

```powershell
docker compose ps
```

Watch backend logs:

```powershell
docker compose logs -f backend
```

Watch frontend logs:

```powershell
docker compose logs -f frontend
```

Stop the project:

```powershell
docker compose down
```

Reset containers and volumes:

```powershell
docker compose down -v
docker compose up -d --build
```

## Local Development Without Docker

This works too, but Docker is the recommended path because it gives you PostgreSQL, Redis, backend, and frontend together.

### Backend

```powershell
cd E:\BlockScope\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd E:\BlockScope\frontend
npm install
npm run dev
```

### Compiler setup for native Slither

If you run locally outside Docker and `solc` is missing:

```powershell
cd E:\BlockScope
python scripts\setup_solc.py 0.8.20
```

## Environment Notes

The repo uses:

- [backend/.env.development](backend/.env.development) for development defaults
- Docker Compose environment overrides for container networking

Important runtime facts:

- In Docker, the backend uses `db` and `redis` service hostnames
- The backend is configured to use Redis-backed rate limiting in the Docker stack
- Swagger docs are enabled
- Health checks are wired and should report database and Redis properly

## API Overview

Main endpoints:

- `GET /`
- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `POST /api/v1/scan`
- `POST /api/v1/scan/file`
- `GET /api/v1/scans`
- `GET /api/v1/scans/{scan_id}`

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for full request and response examples.

## How Scanning Works

BlockScope runs analysis through:

1. input validation
2. Slither parsing and static analysis
3. custom source-rule detection
4. finding normalization and deduplication
5. score calculation
6. persistence to PostgreSQL

The result returned to the user includes:

- `scan_id`
- `contract_name`
- `vulnerabilities_count`
- `severity_breakdown`
- `overall_score`
- `summary`
- `findings`
- `timestamp`

## Security Model

The backend includes:

- security headers
- CORS controls
- request logging
- file validation
- optional API-key-based auth
- Redis-backed rate limiting

Current dev behavior:

- API docs are enabled
- Redis is enabled in the Docker run path
- rate limiting is active in the running Docker stack

## Testing

### Backend tests

From repo root:

```powershell
pytest -q backend
```

Or from the backend directory:

```powershell
cd E:\BlockScope\backend
pytest -q
```

### Frontend tests

```powershell
cd E:\BlockScope\frontend
npm test -- --run
```

### Frontend production build

```powershell
cd E:\BlockScope\frontend
npm run build
```

## Troubleshooting

### Frontend loads but looks broken

Do a hard refresh:

```text
Ctrl + Shift + R
```

### `/health` does not show Redis as `ok`

Check:

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f redis
```

### Swagger loads blank

That issue should now be fixed. If it reappears, rebuild:

```powershell
docker compose down
docker compose up -d --build
```

### Docker daemon is not reachable

Make sure Docker Desktop is open and fully started before running Compose.

### Port already in use

Check whether something else is using:

- `5173`
- `8000`
- `5432`
- `6379`

Then stop the conflicting process or update port mappings.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for a longer issue guide.

## Known Notes

- Some dev/test tooling still emits a Slither `pkg_resources` deprecation warning from an installed dependency. That warning does not block the app.
- The frontend is functional and styled, but still has room for product/UI refinement.
- Docker is the cleanest and most reliable way to run the project right now.

## Documentation Index

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [FAQ.md](FAQ.md)
- [EXAMPLES.md](EXAMPLES.md)
- [SECURITY.md](SECURITY.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Contributing

If you’re contributing:

1. create a branch
2. make your changes
3. run tests
4. open a pull request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
