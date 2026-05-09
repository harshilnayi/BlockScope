# BlockScope – Official Video Tutorial

## Overview

This tutorial walks you through BlockScope, a full-stack smart contract vulnerability scanner for Solidity projects. It demonstrates how to scan contracts, interpret results, and use the React frontend and API.

**▶️ Watch the Tutorial →** [BlockScope Demo Video](https://drive.google.com/file/d/14nlZZgs0lqmPzqBZ3F2Vnh7kh3JhO127/view?usp=sharing)

> **Note:** This video is currently hosted on Google Drive. For long-term reliability, it will be migrated to YouTube. If the link breaks, please open an issue on the repository.

---

## Prerequisites

Before watching or following along, make sure you have:

- **Docker Desktop** installed and running (recommended setup)
- **Git** to clone the repository
- BlockScope running locally:
  ```bash
  git clone https://github.com/harshilnayi/BlockScope.git
  cd BlockScope
  docker compose up -d --build
  ```
- Frontend available at `http://localhost:5173`
- Backend available at `http://localhost:8000`

> For a non-Docker setup, you will also need Python 3.11 and Node.js 20+. See [`README.md`](README.md) for details.

---

## What the Video Covers

| Timestamp | Section              | Description                                         |
|-----------|----------------------|-----------------------------------------------------|
| 0:00      | Introduction         | What BlockScope is and what it solves               |
| 0:45      | Setup & Launch       | Starting the stack with Docker Compose              |
| 2:00      | Frontend Walkthrough | Navigating the React UI                             |
| 2:36      | Scanning a Contract  | Pasting source code and uploading `.sol` files      |
| 3:46      | Reading Scan Results | Interpreting findings, severity, and security score |
| 4:05      | Scan History         | Viewing and filtering previous scans                |
| 4:36      | Summary              | Recap and next steps                                |

---

## Key Features Demonstrated

### 🔍 Dual Analysis Engine
BlockScope runs two layers of analysis on every scan:
- **Slither static analysis** — industry-standard Solidity vulnerability detection
- **Custom source-rule detection** — fallback rules for cases Slither does not cover

### 📊 Security Scoring
Every scan produces:
- An **overall security score** from `0` to `100`
- A **severity breakdown** across findings (e.g., high, medium, low, informational)
- A full findings list with descriptions and line references where available

### 🖥️ Developer-Friendly UI
The React frontend supports:
- **Paste-in editor** — paste Solidity source code directly
- **File upload** — upload `.sol` files for scanning
- **Scan history** — browse all previous scans stored in PostgreSQL
- **Result filtering and export** — narrow down findings by severity

### 🔌 REST API
BlockScope exposes a documented FastAPI backend:
- `POST /api/v1/scan` — scan by JSON payload
- `POST /api/v1/scan/file` — scan by file upload
- `GET /api/v1/scans` — list all previous scans
- `GET /api/v1/scans/{scan_id}` — fetch a specific scan
- Interactive Swagger docs at `http://localhost:8000/docs`

### ⚙️ Operational Reliability
- **Health endpoint** at `/health` — reports database and Redis status
- **Redis-backed rate limiting and caching**
- **Dockerized stack** — one command brings up the frontend, backend, PostgreSQL, and Redis
- **GitHub Actions CI** for backend, frontend, and Docker builds

---

## Step-by-Step Walkthrough

### 1. Start the Stack
```bash
docker compose up -d --build
```
Verify everything is up:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0","database":"ok","redis":"ok"}
```

### 2. Open the Frontend
Navigate to `http://localhost:5173`. If the UI appears outdated, do a hard refresh (`Ctrl+Shift+R`) to clear the browser cache.

### 3. Run Your First Scan
- Paste a Solidity contract into the editor, **or** upload a `.sol` file
- Click **Scan** and wait for results
- Review the security score, severity breakdown, and individual findings

### 4. Explore Scan History
Previously run scans are saved and accessible from the history panel in the UI, or via `GET /api/v1/scans`.

### 5. Try the API Directly
Open `http://localhost:8000/docs` and use the Swagger UI to run scans and fetch results without the frontend.

---

## Screenshots

**Frontend Home Page** — [View Screenshot](https://drive.google.com/file/d/1s5m4S3NYoRJLA82GKVsPpDrkrDOwm_td/view?usp=sharing)

**Scan History** — [View Screenshot](https://drive.google.com/file/d/1z-B7ofjS7gkgInrbnvH6IOLftNLQX7_q/view?usp=sharing)

**Health Endpoint** — [View Screenshot](https://drive.google.com/file/d/1eJPyglcQ2DY0aFiGt93O3ghGDedONBgS/view?usp=sharing)

**Scan Result — No Vulnerabilities** — [View Screenshot](https://drive.google.com/file/d/16Lz9u3-_qYdNnlkiHYenbY7NM3UYazdS/view?usp=sharing)

**Scan Result — Vulnerabilities Detected** — [View Screenshot](https://drive.google.com/file/d/1AE2IVQDrFWG7txtqXjGKUu-hZtyh2--L/view?usp=sharing)

---

## Further Reading

- [`README.md`](README.md) — Full setup and run guide
- [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) — Complete API reference
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — System design overview
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — Common issues and fixes

---

## Feedback

If the video link breaks, or you have questions about the walkthrough, please open an issue on the [BlockScope repository](https://github.com/harshilnayi/BlockScope).
