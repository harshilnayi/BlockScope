#!/bin/bash

echo "Rolling back deployment..."

cd docker
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

echo "Rollback completed."
