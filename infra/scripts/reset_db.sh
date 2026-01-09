#!/usr/bin/env bash
# Reset the development database
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Warning: this will delete all data in the development database."
read -p "Are you sure? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Determine docker compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

cd "$PROJECT_ROOT"

echo "Stopping services and removing volumes..."
$COMPOSE_CMD -f infra/docker/docker-compose.yml down -v

echo "Restarting services..."
$COMPOSE_CMD -f infra/docker/docker-compose.yml up -d postgres redis minio minio-setup

echo "Waiting for services to be ready..."
sleep 5

echo "Database has been reset."
