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
COPY packages/core/pyproject.toml /packages/core/
COPY packages/core/slide2anki_core /packages/core/slide2anki_core

# Install dependencies
RUN uv pip install --system -e /packages/core
RUN uv pip install --system -e .

# Copy worker code
COPY workers/runner/runner /app/runner

# Default command
CMD ["python", "-m", "runner.worker"]
