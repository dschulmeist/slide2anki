# slide2anki-api

FastAPI backend for the slide2anki application.

## Overview

This service provides the REST API for:

- Project and document management
- Background job orchestration
- Authentication and user sessions
- Export endpoints for generated flashcards

## Development

```bash
# Install dependencies
uv venv .venv && source .venv/bin/activate
uv sync

# Run locally
uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000

# Run tests
uv run pytest
```

## API Documentation

Once running, visit http://localhost:8000/docs for interactive Swagger documentation.
