#!/usr/bin/env bash
# Stop the full slide2anki stack (infra + API + worker + web) using Docker Compose.
# Use --prune to remove volumes (all data will be lost).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/infra/docker/docker-compose.yml"

usage() {
  # Display supported flags for stopping the stack.
  echo "Usage: $0 [--prune]" >&2
  echo "  --prune   Remove containers and volumes (destroys data)" >&2
}

require_cmd() {
  # Exit early if a required command-line tool is unavailable.
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

PRUNE_FLAG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prune)
      PRUNE_FLAG="-v"
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

echo "Stopping full stack (infra + api + worker + web)..."
$COMPOSE_CMD -f "$COMPOSE_FILE" --profile full down $PRUNE_FLAG

echo "Stack stopped."
if [[ -n "$PRUNE_FLAG" ]]; then
  echo "Volumes removed; all persisted data has been deleted."
else
  echo "Volumes preserved; rerun ./infra/scripts/run_full_stack.sh to start again."
fi
