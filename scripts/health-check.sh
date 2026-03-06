#!/bin/bash

echo "Checking system health..."

docker ps

echo "Checking backend..."
curl -f http://localhost:8001/docs || echo "Backend unhealthy"

echo "Checking frontend..."
curl -f http://localhost || echo "Frontend unhealthy"

echo "Health check complete."
