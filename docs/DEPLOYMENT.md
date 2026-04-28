# BlockScope — Production Deployment Guide

This document covers deploying the BlockScope platform to production using Docker, with instructions for DigitalOcean, Render, and generic VPS environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Environment Configuration](#environment-configuration)
4. [Deploying on DigitalOcean](#deploying-on-digitalocean)
5. [Deploying on Render](#deploying-on-render)
6. [SSL / HTTPS Setup](#ssl--https-setup)
7. [Database Backups](#database-backups)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Docker** ≥ 24.0 and **Docker Compose** ≥ 2.20
- **Git**
- A domain name (for SSL)
- A server with ≥ 2 GB RAM, 1 vCPU

---

## Quick Start (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/shanaysoni/BlockScope.git
cd BlockScope

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with production values (see below)

# 3. Build and start all services
docker compose -f docker/docker-compose.prod.yml up -d --build

# 4. Verify services are running
docker compose -f docker/docker-compose.prod.yml ps

# 5. Access the API
curl http://localhost/api/v1/info
curl http://localhost/health/live
```

---

## Environment Configuration

Copy `backend/.env.example` to `backend/.env` and set these **required** values:

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://blockscope:STRONG_PASS@postgres:5432/blockscope` |
| `SECRET_KEY` | App secret key (64+ chars) | Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_SECRET_KEY` | JWT signing key (64+ chars) | Generate same way as above |
| `POSTGRES_PASSWORD` | Postgres password (used by Docker) | Must match DATABASE_URL password |
| `REDIS_PASSWORD` | Redis password | Any strong password |
| `ENVIRONMENT` | Deployment environment | `production` |
| `DEBUG` | Debug mode | `false` |
| `METRICS_API_KEY` | Key to access `/metrics` | Any secret string |
| `CORS_ORIGINS` | Allowed frontend origins | `https://yourdomain.com` |

### Generate secure keys

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate strong password
openssl rand -base64 32
```

---

## Deploying on DigitalOcean

### Option A: Droplet (VPS)

1. **Create a Droplet:**
   - Image: Ubuntu 22.04 LTS
   - Plan: Basic, 2 GB RAM / 1 vCPU ($12/mo)
   - Enable monitoring

2. **SSH into the Droplet:**

   ```bash
   ssh root@your-droplet-ip
   ```

3. **Install Docker:**

   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

4. **Clone and deploy:**

   ```bash
   git clone https://github.com/shanaysoni/BlockScope.git
   cd BlockScope
   cp backend/.env.example backend/.env
   nano backend/.env      # Set production values
   docker compose -f docker/docker-compose.prod.yml up -d --build
   ```

5. **Set up firewall:**

   ```bash
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw enable
   ```

### Option B: DigitalOcean App Platform

1. Fork the repository to your GitHub account
2. Go to DigitalOcean → App Platform → Create App
3. Connect your GitHub repo
4. Set environment variables in the App Platform dashboard
5. Deploy — SSL is automatic

---

## Deploying on Render

Render provides the simplest deployment path with automatic SSL.

1. **Create a Render account** at [render.com](https://render.com)

2. **Create a PostgreSQL database:**
   - Dashboard → New → PostgreSQL
   - Note the connection string

3. **Create a Web Service:**
   - Dashboard → New → Web Service
   - Connect your GitHub repo
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4`
   - Add environment variables (DATABASE_URL, SECRET_KEY, etc.)

4. **SSL:** Automatic on Render — no configuration needed.

5. **Access:** Your API is available at `https://your-app.onrender.com`

---

## SSL / HTTPS Setup

### Option A: Let's Encrypt with Certbot (Docker)

Already configured in `docker-compose.prod.yml`. To activate:

```bash
# 1. Ensure port 80 is accessible and DNS points to your server
# 2. Obtain certificate
docker compose -f docker/docker-compose.prod.yml run --rm certbot \
  certonly --webroot --webroot-path=/var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com

# 3. Uncomment the HTTPS server block in docker/nginx/nginx.conf
#    Replace "yourdomain.com" with your actual domain

# 4. Reload nginx
docker exec blockscope-nginx nginx -s reload

# 5. Set up auto-renewal (already handled by certbot container)
```

### Option B: Render/App Platform

SSL is automatic — no action needed.

### Option C: Certbot on bare metal

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot auto-configures nginx and sets up a cron job for renewal.

---

## Database Backups

### Manual backup

```bash
./scripts/backup.sh
```

### Automated daily backups (cron)

```bash
crontab -e
```

Add:

```
0 2 * * * /absolute/path/to/scripts/backup.sh >> /var/log/blockscope-backup.log 2>&1
```

### Verify backups

```bash
# Check backup exists and has reasonable size
ls -lh backups/

# Verify backup is valid (without restoring)
gunzip -t backups/backup_blockscope_2026-04-23_02-00-00.sql.gz
echo $?   # 0 = valid
```

### Restore from backup

```bash
./scripts/restore.sh backups/backup_blockscope_2026-04-23_02-00-00.sql.gz
```

Or manually:

```bash
# Via Docker
gunzip -c backup.sql.gz | docker exec -i blockscope-postgres psql -U blockscope blockscope

# Via local psql
gunzip -c backup.sql.gz | psql -U blockscope blockscope
```

---

## Monitoring

### Health checks

```bash
# Liveness (is the process running?)
curl http://localhost/health/live

# Readiness (are all dependencies healthy?)
curl http://localhost/health/ready

# Startup (has the app finished initialising?)
curl http://localhost/health/startup
```

### Prometheus metrics

Metrics are available at `/metrics` (blocked from external access via nginx).

To access internally:

```bash
docker exec blockscope-backend curl http://localhost:8000/metrics
```

In production, set `METRICS_API_KEY` and pass it via header:

```bash
curl -H "X-Metrics-Key: your-key" http://localhost:8000/metrics
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Container won't start | Check logs: `docker compose -f docker/docker-compose.prod.yml logs backend` |
| Database connection failed | Verify `DATABASE_URL` matches Postgres container credentials |
| 502 Bad Gateway | Backend hasn't started yet — check health with `docker exec blockscope-backend curl localhost:8000/health/live` |
| SSL certificate issues | Ensure DNS A record points to server, port 80 is open |
| Out of disk space | Check backup rotation: `du -sh backups/` |
