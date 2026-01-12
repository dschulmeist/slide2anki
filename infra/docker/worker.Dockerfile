FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package management
RUN pip install uv

# Copy package files
COPY workers/runner/pyproject.toml /app/
COPY workers/runner/README.md /app/README.md
COPY packages/core/pyproject.toml /packages/core/
COPY packages/core/README.md /packages/core/README.md
COPY packages/core/slide2anki_core /packages/core/slide2anki_core

# Copy worker code (needed before editable install)
COPY workers/runner/runner /app/runner

# Install dependencies
RUN uv pip install --system -e /packages/core
RUN uv pip install --system -e .

# Default command
CMD ["python", "-m", "runner.worker"]
