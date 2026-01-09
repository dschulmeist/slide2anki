# slide2anki

slide2anki is a local-first tool that converts image-based lecture PDFs into high-quality Anki flashcards using a LangGraph-driven agent pipeline. Every card is tied to visual evidence on the source slide so users can verify where each fact came from.

## What this project is trying to do

- Treat slides as visual sources of knowledge, not plain text documents.
- Extract atomic claims (definitions, facts, processes, relationships) using vision models.
- Turn claims into focused, one-fact-per-card drafts with minimal wording.
- Critique and deduplicate cards before exporting.
- Keep the user in the loop with a review UI that shows evidence regions.
- Run locally without accounts, relying on the user’s own model endpoint and API key.

## How the pipeline works

1. Ingest a PDF and render each page to an image.
2. Extract atomic claims from each slide image with a vision model.
3. Write Anki card drafts that follow strict formatting rules.
4. Critique cards for ambiguity, redundancy, and weak phrasing.
5. Deduplicate overlapping cards across the deck.
6. Export approved cards to TSV now and APKG later.

## Architecture overview

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

## Local prototype setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+
- A model endpoint and API key (OpenAI or Ollama)

### One command

```bash
git clone https://github.com/yourusername/slide2anki.git
cd slide2anki
./infra/scripts/dev.sh
```

This starts:
- Web UI at http://localhost:3000
- API at http://localhost:8000
- Postgres, Redis, and MinIO

### Manual setup

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

## Configuration

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

POSTGRES_URL=postgresql://slide2anki:slide2anki@localhost:5432/slide2anki
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Using the prototype

1. Upload a PDF on the home page.
2. Track progress on the dashboard.
3. Review cards side-by-side with slide evidence.
4. Export approved cards to TSV.

## Project structure

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

## Development

### Tests

```bash
./tools/lint.sh

cd packages/core && pytest
cd apps/api && pytest
cd apps/web && npm test
```

### Regenerate the API client

```bash
./tools/generate_openapi_client.sh
```

## Roadmap

- PDF upload and rendering
- Basic card generation pipeline
- Review UI with evidence highlighting
- TSV export
- APKG export with embedded images
- Ollama integration
- Batch processing improvements

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Source Available - Personal use only. See [LICENSE](LICENSE) for details.
