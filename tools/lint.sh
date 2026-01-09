#!/usr/bin/env bash
# Run linters and type checks across the project
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Running linters..."

# Python linting with ruff
echo ""
echo "Checking Python code with ruff..."
cd "$PROJECT_ROOT"

if command -v ruff &> /dev/null; then
    ruff check packages/core/
    ruff check apps/api/
    ruff check workers/runner/
    echo "Python linting passed."
else
    echo "Ruff not installed, skipping Python linting."
fi

# Python formatting check
echo ""
echo "Checking Python formatting with black..."
if command -v black &> /dev/null; then
    black --check packages/core/ apps/api/ workers/runner/
    echo "Python formatting check passed."
else
    echo "Black not installed, skipping format check."
fi

# TypeScript linting
echo ""
echo "Checking TypeScript code..."
cd "$PROJECT_ROOT/apps/web"

if [ -f "node_modules/.bin/eslint" ]; then
    npm run lint
    echo "TypeScript linting passed."
else
    echo "ESLint not installed, run 'npm install' first."
fi

echo ""
echo "All checks passed."
