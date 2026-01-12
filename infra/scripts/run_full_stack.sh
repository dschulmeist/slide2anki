#!/usr/bin/env bash
# Run the full slide2anki stack (infra + API + worker + web) using Docker Compose.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker/docker-compose.yml"

usage() {
  # Display supported flags for starting the stack.
  echo "Usage: $0 [--rebuild] [--logs]" >&2
  echo "  --rebuild   Rebuild images before starting" >&2
  echo "  --logs      Stream Docker Compose logs after startup" >&2
}

# Ensure a command is available before proceeding.
require_cmd() {
  # Exit early if a required command-line tool is unavailable.
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

# Parse optional flags.
BUILD_FLAG=""
FOLLOW_LOGS=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rebuild)
      BUILD_FLAG="--build"
      shift
      ;;
    --logs|--follow-logs)
      FOLLOW_LOGS=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

require_cmd docker

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  require_cmd docker-compose
  COMPOSE_CMD="docker-compose"
fi

cd "$PROJECT_ROOT"

echo "Starting full stack (infra + api + worker + web) with Docker Compose..."
$COMPOSE_CMD -f "$COMPOSE_FILE" --profile full up -d postgres redis minio minio-setup api worker web $BUILD_FLAG

echo "Waiting for services to initialize..."
sleep 8

echo "Stack is starting. Key endpoints:"
echo "  API:        http://localhost:8000" 
echo "  API docs:   http://localhost:8000/docs"
echo "  Web:        http://localhost:3000"
echo "  MinIO:      http://localhost:9000 (console http://localhost:9001)"
echo "  Postgres:   localhost:5432"
echo "  Redis:      localhost:6379"
echo

echo "View logs:   $COMPOSE_CMD -f $COMPOSE_FILE --profile full logs -f"
echo "Stop stack:  $COMPOSE_CMD -f $COMPOSE_FILE --profile full down"
echo "Stop script: ./infra/scripts/stop_full_stack.sh [--prune]"
echo

if [[ "$FOLLOW_LOGS" == true ]]; then
  echo "Streaming Docker Compose logs with service prefixes (Ctrl+C to stop; containers keep running)..."
  $COMPOSE_CMD -f "$COMPOSE_FILE" --profile full logs -f
fi
