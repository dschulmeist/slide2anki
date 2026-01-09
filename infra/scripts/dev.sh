#!/usr/bin/env bash
# Start the complete development environment
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Starting slide2anki development environment..."

# Check for required tools
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Determine docker compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

cd "$PROJECT_ROOT"

# Start infrastructure services
echo "Starting infrastructure services (Postgres, Redis, MinIO)..."
$COMPOSE_CMD -f infra/docker/docker-compose.yml up -d postgres redis minio minio-setup

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check if services are healthy
echo "Infrastructure services started."
echo ""
echo "Services:"
echo "  - Postgres:     localhost:5432"
echo "  - Redis:        localhost:6379"
echo "  - MinIO:        localhost:9000 (console: localhost:9001)"
echo ""

# Optionally start API and worker in Docker
if [[ "$1" == "--docker" ]]; then
    echo "Starting API and Worker in Docker..."
    $COMPOSE_CMD -f infra/docker/docker-compose.yml up -d api worker
    echo ""
    echo "  - API:          http://localhost:8000"
    echo "  - API Docs:     http://localhost:8000/docs"
else
    echo "To start the API locally:"
    echo "   cd apps/api && uv pip install -e '.[dev]' && uvicorn app.main:app --reload"
    echo ""
    echo "To start the Worker locally:"
    echo "   cd workers/runner && uv pip install -e '.[dev]' && python -m runner.worker"
fi

echo ""
echo "To start the Web UI locally:"
echo "   cd apps/web && npm install && npm run dev"
echo ""
echo "Development environment is ready."
echo ""
echo "Useful commands:"
echo "  - View logs:     $COMPOSE_CMD -f infra/docker/docker-compose.yml logs -f"
echo "  - Stop all:      $COMPOSE_CMD -f infra/docker/docker-compose.yml down"
echo "  - Reset DB:      ./infra/scripts/reset_db.sh"
