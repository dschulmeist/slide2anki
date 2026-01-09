# slide2anki

A fully local tool that converts image-based lecture PDFs into high-quality Anki flashcards using an agent-driven pipeline.

## Overview

slide2anki treats every slide as a visual source of knowledge rather than assuming machine-readable text. The system:

1. **Ingests** a PDF and renders each page as an image
2. **Extracts** atomic claims (definitions, facts, processes, relationships) using vision models
3. **Writes** focused Anki card drafts following best practices (one fact per card, minimal wording)
4. **Critiques** each card for ambiguity, redundancy, and poor phrasing
5. **Deduplicates** cards across the entire document
6. **Exports** to Anki-compatible formats (TSV, .apkg)

Every card is traceable back to its source slide and evidence region.

## Features

- **Fully Local**: All processing happens on your machine. Bring your own API key.
- **Vision-First**: Works with image-based PDFs, scanned documents, and slides with diagrams
- **Evidence-Based**: Every card links back to the exact slide region it came from
- **Human-in-the-Loop**: Review UI lets you verify, edit, approve, or reject cards
- **Extensible**: Pluggable model backends (OpenAI, Ollama, etc.)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web UI    │────▶│   FastAPI   │────▶│   Redis     │
│  (Next.js)  │◀────│   Backend   │◀────│   Queue     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Postgres   │     │   Worker    │
                    │  (metadata) │     │  (pipeline) │
                    └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   MinIO     │◀────│    Core     │
                    │   (files)   │     │  (LangGraph)│
                    └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+
- An API key for your preferred LLM provider (OpenAI, etc.)

### One Command Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/slide2anki.git
cd slide2anki

# Start everything
./infra/scripts/dev.sh
```

This starts:
- Web UI at http://localhost:3000
- API at http://localhost:8000
- Postgres, Redis, and MinIO

### Manual Setup

```bash
# Start infrastructure
docker-compose -f infra/docker/docker-compose.yml up -d

# Install and run the web app
cd apps/web
npm install
npm run dev

# Install and run the API (in another terminal)
cd apps/api
uv pip install -e ".[dev]"
uvicorn app.main:app --reload

# Run the worker (in another terminal)
cd workers/runner
uv pip install -e ".[dev]"
python -m runner.worker
```

## Project Structure

```
slide2anki/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── packages/
│   ├── core/         # LangGraph pipeline (framework-agnostic)
│   └── shared/       # OpenAPI specs and generated clients
├── workers/
│   └── runner/       # Background job worker
├── infra/
│   ├── docker/       # Docker Compose for local dev
│   └── scripts/      # Development scripts
└── data/
    ├── samples/      # Sample PDFs for testing
    └── fixtures/     # Test fixtures
```

## Configuration

Create a `.env` file in the root directory:

```env
# LLM Configuration
OPENAI_API_KEY=sk-...
# Or for Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Storage (defaults work for local dev)
POSTGRES_URL=postgresql://slide2anki:slide2anki@localhost:5432/slide2anki
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Usage

1. **Upload**: Drop a PDF on the upload page
2. **Process**: Watch the pipeline progress in real-time
3. **Review**: Examine each card alongside its source slide
4. **Export**: Download as TSV or .apkg file

## Development

### Running Tests

```bash
# All tests
./tools/lint.sh

# Python tests
cd packages/core && pytest
cd apps/api && pytest

# TypeScript tests
cd apps/web && npm test
```

### Regenerating API Client

After modifying the API, regenerate the TypeScript client:

```bash
./tools/generate_openapi_client.sh
```

## Roadmap

- [x] Repository structure and dev environment
- [ ] PDF upload and rendering
- [ ] Basic card generation pipeline
- [ ] Review UI with evidence highlighting
- [ ] TSV export
- [ ] .apkg export with embedded images
- [ ] Ollama integration
- [ ] Batch processing improvements

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Source Available - Personal use only. See [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) for the agent pipeline
- [Next.js](https://nextjs.org/) for the web interface
- [FastAPI](https://fastapi.tiangolo.com/) for the backend API
- [genanki](https://github.com/kerrickstaley/genanki) for Anki deck generation
