#!/bin/bash
# =============================================================================
# BlockScope — Production Deployment Script
# =============================================================================
# Deploys the full stack using Docker Compose.
#
# Usage:
#   ./scripts/deploy.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.prod.yml"

echo "[$(date)] Starting BlockScope production deployment..."

# Validate environment file exists
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
    echo "ERROR: backend/.env not found. Copy backend/.env.example and configure it."
    exit 1
fi

# Stop existing containers
echo "[$(date)] Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down

# Build images
echo "[$(date)] Building images..."
docker compose -f "$COMPOSE_FILE" build

# Start services
echo "[$(date)] Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for backend to be ready
echo "[$(date)] Waiting for backend health check..."
for i in $(seq 1 30); do
    if docker exec blockscope-backend curl -sf http://localhost:8000/health/live > /dev/null 2>&1; then
        echo "[$(date)] Backend is healthy."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[$(date)] WARNING: Backend health check timed out after 30 seconds."
        docker compose -f "$COMPOSE_FILE" logs --tail=20 backend
    fi
    sleep 1
done

# Show running containers
echo ""
echo "[$(date)] Running containers:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "[$(date)] Deployment completed successfully."
