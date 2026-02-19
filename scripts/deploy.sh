#!/bin/bash

echo "Starting BlockScope production deployment..."

cd ../docker || exit

docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "Deployment completed."
