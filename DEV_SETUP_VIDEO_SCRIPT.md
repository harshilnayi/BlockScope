# BlockScope – Developer Setup Walkthrough Script

## Duration: 6–8 Minutes

Audience: New contributors
Goal: Get development environment running successfully

---

## 1. Introduction (0:00 – 0:45)

**On Screen: Repository homepage**

**Script:**
> Welcome to the BlockScope developer onboarding guide.
>
> In this video, I'll show you how to:
>
> - Clone the repository
> - Run the full stack using Docker
> - Run the backend locally for development
> - Run the frontend in dev mode
> - Verify everything works
>
> By the end, you'll have a fully working development setup.

---

## 2. Clone the Repository (0:45 – 1:15)

**On Screen: Terminal**

    git clone https://github.com/harshilnayi/BlockScope.git
    cd BlockScope

Make sure you are on the latest main branch:

    git checkout main
    git pull origin main

---

## 3. Option 1 – Docker Setup (Recommended for Quick Start) (1:15 – 3:00)

**Explain:**
> BlockScope includes a production-style Docker setup that runs:
>
> - FastAPI backend
> - React frontend
> - PostgreSQL
> - Redis
> - Nginx reverse proxy

Start everything:

    docker compose -f docker/docker-compose.prod.yml up --build

Wait for containers to build.

Verify:

    docker ps

Open browser:

    http://localhost

**Explain:**
> The frontend is served through Nginx.
> API requests are proxied to the backend container.

Test health:

    http://localhost/health

Expected response:

    {
      "status": "healthy",
      "version": "1.0.0",
      "app": "BlockScope API"
    }

> If you see this, your Docker setup is working.

---

## 4. Option 2 – Local Backend Development (3:00 – 5:00)

**Explain:**
> For active backend development and debugging, running locally is recommended.

Navigate to backend:

    cd backend
    python3 -m venv venv
    source venv/bin/activate  # Windows: .\venv\Scripts\activate
    pip install -r requirements.txt

Make sure PostgreSQL is running locally.

Start backend:

    uvicorn app.main:app --reload

Open Swagger:

    http://localhost:8000/docs

**Explain:**
> Swagger allows you to test endpoints directly.
> The main scan endpoint is:
>
> `POST /api/v1/scan`

---

## 5. Frontend Local Development (5:00 – 6:00)

Navigate to frontend:

    cd frontend
    npm install
    npm run dev

Open:

    http://localhost:5173

**Explain:**
> In development mode, Vite serves the frontend.
> Ensure the backend is running before testing scans.

---

## 6. Running Tests (Optional) (6:00 – 6:45)

Navigate to backend:

    cd backend
    pytest

**Explain:**
> All tests must pass before opening a pull request.

---

## 7. Making Your First Contribution (6:45 – 7:30)

Create a new branch:

    git checkout -b feat/your-feature-name

Make changes.

Commit using conventional format:

    git commit -m "feat: add new analysis rule"

Push:

    git push origin feat/your-feature-name

Open a pull request to `main`.

---

## 8. Closing (7:30 – 8:00)

**Explain:**
> Before submitting your PR:
>
> - Ensure Docker still works
> - Ensure backend starts
> - Ensure frontend builds
> - Review the `CODE_REVIEW_CHECKLIST.md`
>
> Thank you for contributing to BlockScope.