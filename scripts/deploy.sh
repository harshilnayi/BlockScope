#!/bin/bash
set -e

echo "Starting BlockScope production deployment..."

# Get absolute path to this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/../docker"

cd "$DOCKER_DIR" || { echo "Failed to enter docker directory"; exit 1; }

echo "Stopping existing containers..."
docker compose -f docker-compose.prod.yml down

echo "Building images..."
docker compose -f docker-compose.prod.yml build

echo "Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo "Verifying running containers..."
docker compose -f docker-compose.prod.yml ps

echo "Deployment completed successfully."
