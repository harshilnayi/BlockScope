# BlockScope – Official Video Tutorial Script

---

## 🎬 Duration: ~6–8 Minutes

Audience: Developers, reviewers, contributors  
Environment: Docker + React frontend

---

# 🎬 1. Introduction (0:00 – 0:45)

**On Screen: Project README + Logo**

🎙️ Script:

> Welcome to BlockScope.
>
> BlockScope is a smart contract vulnerability scanner built with FastAPI and React.
>
> It allows developers to submit Solidity contracts, analyze them for security issues, and store structured scan results in a PostgreSQL database.
>
> In this walkthrough, I'll show you how to run the full production setup using Docker, submit a contract, and review the results.

---

# 🐳 2. Running BlockScope with Docker (0:45 – 2:00)

**On Screen: Terminal in project root**

🎙️ Script:

> BlockScope includes a production-ready Docker setup with:
>
> * FastAPI backend
> * React frontend
> * PostgreSQL database
> * Redis
> * Nginx reverse proxy
>
> To start everything, run:

```bash
docker compose -f docker/docker-compose.prod.yml up --build
```

Pause while containers build.

🎙️ Continue:

> This builds multi-stage images for both backend and frontend and starts all services on a private Docker network.

---

## ✅ Verify Containers

```bash
docker ps
```

🎙️ Script:

> We can confirm that all containers are running — backend, frontend, database, Redis, and Nginx.

---

# 🌐 3. Open the Application (2:00 – 2:45)

**On Screen: Browser → http://localhost**

🎙️ Script:

> The Nginx reverse proxy exposes port 80.
>
> Opening `http://localhost` loads the React frontend.

Show frontend UI.

---

# 🩺 4. Health Check (2:45 – 3:15)

**On Screen: Browser → http://localhost/health**

🎙️ Script:

> The backend exposes a `/health` endpoint.
>
> It confirms:
>
> * API status
> * Version
> * Database connectivity

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "app": "BlockScope API"
}
```

---

# 📄 5. Submitting a Contract Scan (3:15 – 4:30)

**On Screen: React UI**

Paste example contract:

```solidity
pragma solidity ^0.8.0;

contract SafeCounter {
    uint public count;

    function increment() public {
        count += 1;
    }
}
```

Click "Scan".

🎙️ Script:

> When we submit a contract:
>
> 1. The frontend sends a POST request to `/api/v1/scan`
> 2. The backend validates the request
> 3. The AnalysisOrchestrator processes the code
> 4. Results are stored in PostgreSQL
> 5. A structured JSON response is returned

Show response on UI.

Expected output:

```json
{
  "scan_id": 1,
  "contract_name": "SafeCounter",
  "vulnerabilities_count": 0,
  "overall_score": 100
}
```

---

# ⚙️ Important Note About Analysis (4:30 – 5:00)

🎙️ Script:

> BlockScope uses a rule-based analysis engine.
>
> Vulnerability detection depends on the configured rule set inside the AnalysisOrchestrator.
>
> If no rules are loaded, contracts will return as SAFE.
>
> The architecture supports extensible security rules for advanced scanning.

---

# 📚 6. Viewing Stored Scans (5:00 – 5:45)

**On Screen:**

```
http://localhost/api/v1/scans
```

🎙️ Script:

> All scans are stored in PostgreSQL and can be retrieved using:
>
> GET `/api/v1/scans`

Show list.

Explain pagination briefly:

```
/api/v1/scans?skip=0&limit=10
```

---

# 🔎 7. Retrieve Specific Scan (5:45 – 6:15)

Open:

```
http://localhost/api/v1/scans/1
```

🎙️ Script:

> Each scan can also be retrieved individually by ID.

---

# 🧠 8. Architecture Overview (6:15 – 7:00)

🎙️ Script:

> BlockScope includes:
>
> * Multi-stage Docker builds
> * Production-ready Nginx reverse proxy
> * PostgreSQL persistence
> * Redis integration
> * Health checks
> * Structured JSON API
>
> The backend is built using FastAPI and SQLAlchemy.
> The frontend is built with React and Vite.
>
> The system is modular and designed for extensibility.

---

# 🏁 9. Closing (7:00 – 7:30)

🎙️ Script:

> This concludes the BlockScope walkthrough.
>
> For detailed documentation, refer to:
>
> * USER_GUIDE.md
> * FAQ.md
> * EXAMPLES.md
>
> Thank you for watching.

---
