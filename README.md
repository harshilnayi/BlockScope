# BlockScope

[![Backend CI](https://github.com/harshilnayi/BlockScope/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/harshilnayi/BlockScope/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/frontend-ci.yml)
[![Docker Build](https://github.com/harshilnayi/BlockScope/actions/workflows/docker-build.yml/badge.svg)](https://github.com/harshilnayi/BlockScope/actions/workflows/docker-build.yml)
[![codecov](https://codecov.io/gh/harshilnayi/BlockScope/branch/main/graph/badge.svg)](https://codecov.io/gh/harshilnayi/BlockScope)

**Production-grade smart contract vulnerability scanner with ML-powered detection.**

BlockScope analyzes Solidity smart contracts for security vulnerabilities using [Slither](https://github.com/crytic/slither) static analysis combined with custom detection rules. It produces scored security reports with actionable remediation guidance.

---

## ✨ Features

- **Automated Vulnerability Scanning** — Paste source code or upload `.sol` files via REST API
- **Dual Analysis Engine** — Slither static analysis + custom pattern-based rules
- **Security Scoring** — 0–100 score with severity breakdown (critical, high, medium, low)
- **Finding Deduplication** — Merges results from multiple engines, keeps the most detailed
- **API Key Authentication** — Tiered access (free, basic, premium, enterprise)
- **Rate Limiting** — Redis-backed sliding-window throttling
- **Production Security** — OWASP headers, CORS, XSS/SQL injection protection, file validation
- **Full CI/CD** — GitHub Actions for testing, linting, Docker builds, and deployment

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/harshilnayi/BlockScope.git
cd BlockScope

# 2. Configure
cp backend/.env.example backend/.env.development

# 3. Run
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React · Vite · TailwindCSS |
| **Backend** | FastAPI · Python 3.11 · Uvicorn |
| **Database** | PostgreSQL 15 · SQLAlchemy · Alembic |
| **Cache** | Redis 7 |
| **Analysis** | Slither · Custom Rule Engine |
| **Infra** | Docker · Nginx · GitHub Actions |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System design, data models, analysis pipeline, security layers |
| [**API_DOCUMENTATION.md**](API_DOCUMENTATION.md) | Complete endpoint reference with request/response examples |
| [**DEPLOYMENT.md**](DEPLOYMENT.md) | Step-by-step setup for development and production |
| [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md) | Common issues and solutions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [SECURITY.md](SECURITY.md) | Security policy and reporting |
| [FAQ.md](FAQ.md) | Frequently asked questions |
| [EXAMPLES.md](EXAMPLES.md) | Usage examples |

---

## 📁 Project Structure

```
BlockScope/
├── backend/              # FastAPI backend
│   ├── app/              #   Application code
│   │   ├── core/         #     Config, auth, security, rate limiting
│   │   ├── routers/      #     API endpoints
│   │   ├── models/       #     SQLAlchemy database models
│   │   └── schemas/      #     Pydantic request/response schemas
│   ├── analysis/         #   Vulnerability analysis engine
│   │   ├── orchestrator.py   # Analysis pipeline coordinator
│   │   ├── slither_wrapper.py # Slither integration
│   │   └── rules/        #     Custom detection rules
│   └── tests/            #   Pytest test suite
├── frontend/             # React + Vite frontend
│   └── src/              #   React components and pages
├── docker/               # Dockerfiles (dev + prod)
│   └── nginx/            #   Nginx configs
├── scripts/              # deploy.sh, backup.sh, rollback.sh
└── .github/workflows/    # CI/CD pipelines
```

---

## 🔑 API Quick Reference

```bash
# Scan source code
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"source_code": "pragma solidity ^0.8.0; contract Test { ... }"}'

# Upload a file
curl -X POST http://localhost:8000/api/v1/scan/file \
  -F "file=@MyContract.sol"

# List scans
curl http://localhost:8000/api/v1/scans?limit=10

# Get scan details
curl http://localhost:8000/api/v1/scans/42
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for the complete reference.

---

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
