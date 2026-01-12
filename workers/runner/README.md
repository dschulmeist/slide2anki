# slide2anki-runner

Background job worker for the slide2anki application.

## Overview

This worker processes queued jobs for:

- PDF rendering and slide extraction
- Claim extraction via vision models
- Flashcard generation and critique
- Export packaging

It connects to Redis for job queuing and PostgreSQL/MinIO for persistence.

## Development

```bash
# Install dependencies
uv venv .venv && source .venv/bin/activate
uv sync

# Run worker
uv run python -m runner.worker

# Run tests
uv run pytest
```

## Configuration

Set environment variables (or use a `.env` file):

- `DATABASE_URL` – PostgreSQL connection string
- `REDIS_URL` – Redis connection string
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- `OPENAI_API_KEY` or `OLLAMA_BASE_URL` for model inference
