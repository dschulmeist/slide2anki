#!/usr/bin/env bash
# Generate TypeScript client from OpenAPI spec
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Generating TypeScript client from OpenAPI spec..."

cd "$PROJECT_ROOT/packages/shared"

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Generate the client
echo "Generating types..."
npm run generate

echo "TypeScript client generated at packages/shared/ts-client/index.ts."

# Copy to web app if needed
if [ -d "$PROJECT_ROOT/apps/web/lib/api" ]; then
    echo "Copying types to web app..."
    cp "$PROJECT_ROOT/packages/shared/ts-client/index.ts" "$PROJECT_ROOT/apps/web/lib/api/types.ts"
    echo "Types copied to apps/web/lib/api/types.ts."
fi

echo ""
echo "Done."
