# BlockScope User Guide

## Overview

BlockScope is a production-ready smart contract vulnerability scanner built using:

- FastAPI (Backend)
- React (Frontend)
- PostgreSQL (Database)
- Redis (Cache / Rate limiting)
- Nginx (Reverse Proxy)
- Docker Compose (Deployment)

---

## Requirements

Install:

- Docker
- Docker Compose
- Git

Verify:

docker --version  
docker compose version  

---

## Installation

Clone repository:

git clone https://github.com/harshilnayi/BlockScope.git  
cd BlockScope  

---

## Environment Setup

Production requires a backend environment file.

Create it:

cp backend/backend.env.production.example backend/.env  

Edit backend/.env and set:

POSTGRES_PASSWORD=your_password  
REDIS_PASSWORD=your_password  

⚠ Never commit backend/.env

---

## Run in Production Mode

Start the application:

cd scripts  
./deploy.sh  

This will:

- Build backend and frontend
- Start PostgreSQL and Redis
- Start Nginx
- Start API server

---

## Access Application

Open:

http://localhost  

Frontend is served through Nginx.

---

## API Endpoints

### Scan Smart Contract

POST  
http://localhost/api/v1/scan  

Example:

curl -X POST http://localhost/api/v1/scan \
-H "Content-Type: application/json" \
-d '{
  "source_code": "contract Test {}",
  "contract_name": "Test"
}'

---

### Health Check

GET  
http://localhost/health  

Returns:

{
  "status": "healthy",
  "version": "0.1.0",
  "app": "BlockScope API"
}

---

### API Info

GET  
http://localhost/api/v1/info  

---

## Backup Database

cd scripts  
./backup.sh  

Creates file:

backup-YYYY-MM-DD-HH-MM.sql.gz  

---

## Restore Database

cd scripts  
./rollback.sh backup-file.sql.gz  

---

## View Running Services

docker compose -f docker/docker-compose.prod.yml ps  

View backend logs:

docker logs blockscope-backend  

---

## Stop Application

cd docker  
docker compose -f docker-compose.prod.yml down  

---

## Troubleshooting

### Containers not starting

docker compose -f docker/docker-compose.prod.yml logs  

### Health check failing

Visit:

http://localhost/health  

---

## Security Notes

- Never commit backend/.env
- Always set strong passwords
- Only Nginx exposes port 80
- Backend and database are internal only

---

## License

MIT License
