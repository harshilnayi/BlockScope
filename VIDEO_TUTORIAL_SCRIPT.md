# BlockScope – Official Video Tutorial Script

---

## 🎬 Duration: ~5 Minutes

Audience: Developers, reviewers, contributors  
Environment: Docker + React frontend

---

# 🎬 1. Introduction (0:00 – 0:45)

**On Screen: Project README + Logo**

🎙️ Script:

> Welcome to BlockScope.
>
> BlockScope is a full-stack smart contract vulnerability scanner built with FastAPI and React.
>
> It allows developers to submit Solidity contracts, analyze them for security issues using a dual analysis engine — Slither static analysis combined with custom source-rule detection — and store structured scan results in a PostgreSQL database.
>
> In this walkthrough, I'll show you how to run the full stack using Docker, submit a contract, and interpret the scan results.

---

# 🐳 2. Setup & Launch (0:45 – 2:00)

**On Screen: Terminal in project root**

🎙️ Script:

> First, clone the repository and start the stack with a single command:

```bash
git clone https://github.com/harshilnayi/BlockScope.git
cd BlockScope
docker compose up -d --build
```

Pause while containers build.

🎙️ Continue:

> This brings up all services — the FastAPI backend, React frontend, PostgreSQL database, and Redis — in detached mode.
>
> Once everything is up, verify the backend is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "ok",
  "redis": "ok"
}
```

> The health endpoint confirms the API, database, and Redis are all operational.

---

# 🌐 3. Frontend Walkthrough (2:00 – 2:36)

**On Screen: Browser → http://localhost:5173**

🎙️ Script:

> The React frontend is available at `http://localhost:5173`.
>
> If the UI looks outdated after a rebuild, do a hard refresh — `Ctrl+Shift+R` — to clear the browser cache.
>
> From the main screen, you can either paste Solidity source code directly into the editor, or upload a `.sol` file for scanning.

Show frontend UI — highlight the paste editor and file upload controls.

---

# 📄 4. Scanning a Contract (2:36 – 3:46)

**On Screen: React UI — paste editor**

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

Click **Scan**.

🎙️ Script:

> When we submit a contract:
>
> 1. The frontend sends a POST request to `/api/v1/scan`
> 2. The backend validates the input and passes it through the dual analysis engine
> 3. Slither performs industry-standard static analysis
> 4. Custom source rules run as a fallback for anything Slither doesn't cover
> 5. Results are stored in PostgreSQL and a structured response is returned

Show response on UI.

---

# 📊 5. Reading Scan Results (3:46 – 4:05)

**On Screen: Scan results panel in the React UI**

🎙️ Script:

> Every scan produces an overall security score from 0 to 100, along with a severity breakdown across all findings — high, medium, low, and informational.
>
> Each finding includes a description and, where available, line references pointing to the exact location in the contract source.
>
> A clean contract like `SafeCounter` will score 100, with zero findings.

Show the security score, severity breakdown, and findings list.

---

# 📚 6. Scan History (4:05 – 4:36)

**On Screen: Scan history panel in the React UI**

🎙️ Script:

> All previous scans are saved and accessible from the history panel.
>
> You can filter results by severity to narrow down findings across past scans.
>
> The same data is also available directly via the REST API:

```
GET http://localhost:8000/api/v1/scans
GET http://localhost:8000/api/v1/scans/{scan_id}
```

> And for developers who prefer working without the frontend, the full API is documented interactively at:

```
http://localhost:8000/docs
```

> The Swagger UI lets you run scans and fetch results directly from the browser.

---

# 🏁 7. Summary (4:36 – end)

🎙️ Script:

> That wraps up the BlockScope walkthrough. To recap:
>
> * Start the stack with `docker compose up -d --build`
> * Open the React frontend at `http://localhost:5173`
> * Paste or upload a Solidity contract and click **Scan**
> * Review your security score, severity breakdown, and findings
> * Browse previous scans in the history panel or via the REST API
>
> For further reading, refer to:
>
> * `README.md` — full setup and run guide
> * `API_DOCUMENTATION.md` — complete API reference
> * `ARCHITECTURE.md` — system design overview
> * `TROUBLESHOOTING.md` — common issues and fixes
>
> If you run into any issues or the video link breaks, please open an issue on the BlockScope repository.
>
> Thank you for watching.

---