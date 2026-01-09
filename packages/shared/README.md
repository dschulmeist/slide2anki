# Shared Package

This package contains the OpenAPI specification and generated TypeScript client for the slide2anki API.

## Structure

```
shared/
├── openapi/
│   └── openapi.yaml    # OpenAPI 3.1 specification
└── ts-client/          # Generated TypeScript client
```

## Generating the TypeScript Client

After modifying `openapi/openapi.yaml`, regenerate the TypeScript client:

```bash
# From the repository root
./tools/generate_openapi_client.sh
```

This uses `openapi-typescript` to generate types from the OpenAPI spec.

## Usage in Web App

```typescript
import type { components } from '@slide2anki/shared/ts-client';

type Deck = components['schemas']['Deck'];
type Card = components['schemas']['Card'];
```

## Keeping Types in Sync

1. Make changes to `openapi/openapi.yaml`
2. Run the generation script
3. The web app will automatically use the new types
