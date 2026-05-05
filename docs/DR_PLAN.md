# BlockScope — Disaster Recovery Plan

This document defines the disaster recovery (DR) procedures for the BlockScope platform, including recovery objectives, step-by-step procedures, and verification checklists.

---

## Recovery Objectives

| Metric | Target | Description |
|---|---|---|
| **RTO** (Recovery Time Objective) | **< 1 hour** | Maximum acceptable time from failure detection to full service restoration |
| **RPO** (Recovery Point Objective) | **< 24 hours** | Maximum acceptable data loss, determined by backup frequency (daily at 2 AM) |

---

## Disaster Scenarios

### Scenario 1: Server Crash (Complete Loss)

**Symptoms:** Server unreachable, all services down.

**Recovery Steps:**

1. **Provision a new server**

   ```bash
   # DigitalOcean example
   doctl compute droplet create blockscope-prod \
     --image ubuntu-22-04-x64 \
     --size s-2vcpu-2gb \
     --region nyc1
   ```

   Or create via the DigitalOcean/Render dashboard.

2. **Install Docker on the new server**

   ```bash
   ssh root@NEW_SERVER_IP
   curl -fsSL https://get.docker.com | sh
   ```

3. **Clone the repository**

   ```bash
   git clone https://github.com/harshilnayi/BlockScope.git
   cd BlockScope
   ```

4. **Restore environment configuration**

   ```bash
   cp backend/.env.example backend/.env
   # Restore production values from your secure secrets store
   nano backend/.env
   ```

5. **Deploy the application**

   ```bash
   docker compose -f docker/docker-compose.prod.yml up -d --build
   ```

6. **Restore the database from the latest backup**

   ```bash
   # Transfer backup from off-site storage
   scp user@backup-server:/backups/latest.sql.gz ./backups/

   # Restore
   ./scripts/restore.sh backups/latest.sql.gz
   ```

7. **Update DNS records**

   Point your domain's A record to the new server IP.

8. **Restore SSL certificates**

   ```bash
   docker compose -f docker/docker-compose.prod.yml run --rm certbot \
     certonly --webroot --webroot-path=/var/www/certbot \
     -d yourdomain.com
   docker exec blockscope-nginx nginx -s reload
   ```

9. **Verify recovery** (see checklist below)

---

### Scenario 2: Database Corruption

**Symptoms:** Application errors, inconsistent data, migration failures.

**Recovery Steps:**

1. **Stop the backend** to prevent further writes:

   ```bash
   docker compose -f docker/docker-compose.prod.yml stop backend
   ```

2. **Drop and recreate the database:**

   ```bash
   docker exec blockscope-postgres psql -U blockscope -c "DROP DATABASE blockscope;"
   docker exec blockscope-postgres psql -U blockscope -c "CREATE DATABASE blockscope;"
   ```

3. **Restore from latest backup:**

   ```bash
   ./scripts/restore.sh backups/backup_blockscope_YYYY-MM-DD_HH-MM-SS.sql.gz
   ```

4. **Restart the backend:**

   ```bash
   docker compose -f docker/docker-compose.prod.yml start backend
   ```

5. **Verify data integrity** by checking scan counts and recent records.

---

### Scenario 3: Application Deployment Failure

**Symptoms:** New deployment causes errors, API returns 500s.

**Recovery Steps:**

1. **Rollback to previous version:**

   ```bash
   ./scripts/rollback.sh backup_blockscope_YYYY-MM-DD.sql.gz
   ```

   Or revert the Docker image:

   ```bash
   docker compose -f docker/docker-compose.prod.yml down
   git checkout <last-known-good-commit>
   docker compose -f docker/docker-compose.prod.yml up -d --build
   ```

2. **Check logs for the root cause:**

   ```bash
   docker compose -f docker/docker-compose.prod.yml logs --tail=100 backend
   ```

---

### Scenario 4: Redis Failure

**Symptoms:** Rate limiting not working, potential slow responses.

**Impact:** Low — the application operates without Redis (rate limiting disabled).

**Recovery:**

```bash
docker compose -f docker/docker-compose.prod.yml restart redis
```

---

## Recovery Verification Checklist

After any recovery, verify all systems:

| Check | Command | Expected Result |
|---|---|---|
| Backend is running | `curl http://localhost/health/live` | `{"status": "alive"}` |
| Database is connected | `curl http://localhost/health/ready` | `database.status == "ok"` |
| API responds correctly | `curl http://localhost/api/v1/info` | Returns JSON with version info |
| Scan endpoint works | `curl -X POST http://localhost/api/v1/scan -H "Content-Type: application/json" -d '{"source_code": "pragma solidity ^0.8.0; contract Test { }"}'` | Returns scan result |
| SSL is working | `curl https://yourdomain.com/health/live` | No certificate errors |
| Backups are scheduled | `crontab -l` | Shows backup cron entry |

---

## Backup Strategy

| Item | Frequency | Retention | Storage |
|---|---|---|---|
| Database (pg_dump) | Daily at 2 AM | 30 days | Local + off-site |
| Application code | Every push | Unlimited | GitHub |
| Environment config | On change | Current | Secure secrets manager |
| SSL certificates | Auto-renewed | 90 days | Let's Encrypt |

### Off-site backup recommendation

Copy backups to a remote location:

```bash
# Add to cron after backup runs (e.g., 3 AM)
0 3 * * * rsync -az /path/to/backups/ user@backup-server:/blockscope-backups/
```

Or to object storage:

```bash
# AWS S3
0 3 * * * aws s3 sync /path/to/backups/ s3://blockscope-backups/ --delete
```

---

## Communication Plan

| Event | Notify | Channel |
|---|---|---|
| Service outage detected | Engineering team | Slack/Discord |
| Recovery started | Team lead | Slack/Discord |
| Recovery verified | All stakeholders | Email + Slack |

---

## Post-Incident Review

After every recovery:

1. **Document** what happened (timeline, root cause)
2. **Identify** what could have prevented or shortened the outage
3. **Update** this DR plan with lessons learned
4. **Test** the updated recovery procedure within 30 days

---

## DR Drill Schedule

Conduct DR drills quarterly:

1. Spin up a test server
2. Restore from the latest backup
3. Verify all checklist items pass
4. Record the actual RTO achieved
5. Report findings

**Last tested:** _Not yet — schedule first drill after production deployment._
