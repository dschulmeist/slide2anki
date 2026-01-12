# slide2anki

slide2anki is a local-first tool that converts image-based lecture PDFs into high-quality Anki flashcards using a LangGraph-driven agent pipeline. Every card is tied to visual evidence on the source slide so users can verify where each fact came from.

## What this project is trying to do

- Ideally the user can dump all the documents he has (e.g. for a course all teh lecture slides, exercises and past exams etc.)
- then the system consisting of several agents decomposes all that, converts it maybe into a markdown file, so all formulas etc. can be preserved. Diagrams may be replicated as ascii (A better path is to store image regions and reference them directly in markdown or as embedded images.)?
- Then based on this comprehensive script, we create flashcards that cover as much content as possible (of course the user can decide and give instructions).
- Later this comprehensiv markdown is stored in the backend as source of truth and if the user adds documents this markdown gets updated.  likely need versioned markdown snapshots + user edits tracked separately. 
- The user can tehn review the created flashcards, and also suggest changes, select flashcards and request changes on a subset. 
- The user can also see the markdown doc.
- Treat slides as visual sources of knowledge, not plain text documents.
- Extract content and atomic claims (definitions, facts, processes, relationships) using vision models.
- Turn claims into focused, one-fact-per-card drafts with minimal wording while retaianing all important information.
- Critique and deduplicate cards before exporting.
- Keep the user in the loop with a review UI that shows evidence regions.
- Run locally without accounts, relying on the user’s own model endpoint and API key.

LATER WORK:
- deploy on the web with user accounts etc.
- implement own flashcard study system similar to anki to study and review teh flashcards. Also include some AI based features in there.
- implement some sort of web grounding/augmentation to improve the quality of the flashcards
       
## How the pipeline works

1. Ingest a PDF and render each page to an image.
2. Extract atomic claims from each slide image with a vision model.
3. Write Anki card drafts that follow strict formatting rules.
4. Critique cards for ambiguity, redundancy, and weak phrasing.
5. Deduplicate overlapping cards across the deck.
6. Export approved cards to TSV or APKG format.

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

### Component responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Web UI** | Next.js 14, React 18, Tailwind, Zustand | User interface for uploads, review, settings |
| **API** | FastAPI, SQLAlchemy, asyncpg | REST endpoints, request validation, job dispatch |
| **Queue** | Redis + RQ | Decouples long-running tasks from HTTP requests |
| **Worker** | Python worker process | Executes pipeline jobs, updates progress |
| **Postgres** | PostgreSQL 16 | Stores projects, documents, markdown, cards, jobs |
| **MinIO** | S3-compatible storage | Stores PDFs, slide images, exports |
| **Core** | LangGraph, LangChain, Pydantic | Framework-agnostic extraction and generation logic |

### Data model

```
Project (workspace)
  ├── Document (uploaded PDF)
  │     └── Slide (rendered page image)
  │           └── Claim (extracted atomic fact)
  ├── Chapter (inferred section)
  │     └── MarkdownBlock (canonical content unit)
  ├── MarkdownVersion (full snapshot for rollback)
  ├── Deck (flashcard collection)
  │     └── CardDraft (generated card)
  │           └── CardRevision (edit history)
  ├── GenerationConfig (card generation settings)
  └── Job (async task with JobEvent log)
```

### Pipeline graphs (LangGraph)

The core package defines multiple composable graphs:

| Graph | Purpose | Key Nodes |
|-------|---------|-----------|
| `build_markdown_graph` | Extract content from slides into canonical markdown | ingest, render, segment, extract, verify, markdown |
| `build_card_graph` | Generate flashcards from markdown blocks | write_cards, critique, repair, dedupe |
| `build_slide_graph` | Simple slide-level extraction | extract, write_cards, dedupe, export |
| `build_region_graph` | Region-aware extraction for complex slides | segment, extract_region, verify, repair |

### Request lifecycle

1. User uploads PDF via Web UI
2. API creates `Document` record, stores PDF in MinIO, enqueues `markdown_build` job
3. Worker dequeues job, runs markdown graph, persists `MarkdownBlock` rows
4. User reviews markdown, selects chapters, clicks "Generate Deck"
5. API creates `Deck` record, enqueues `deck_generation` job
6. Worker runs card graph, persists `CardDraft` rows
7. User reviews cards, approves/rejects, requests export
8. Worker generates TSV/APKG file, uploads to MinIO
9. User downloads export

### Model provider abstraction

The core package uses a `BaseModelAdapter` interface for LLM calls:

- **OpenAIAdapter**: OpenAI API, OpenRouter, and compatible endpoints
- **OllamaAdapter**: Local Ollama instances

Configuration is stored in `AppSetting` (Postgres) and loaded by workers at runtime.

### Tech stack summary

**Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Redis, MinIO SDK, LangGraph, LangChain, Pydantic 2, pdf2image, Pillow, genanki

**Frontend**: Node.js 20+, Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand, SWR

**Infrastructure**: Docker, Docker Compose, PostgreSQL 16, Redis 7, MinIO

## Local prototype setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+
- A model endpoint and API key (configured in the web UI)

### One command (Docker full stack)

```bash
git clone https://github.com/yourusername/slide2anki.git
cd slide2anki
./infra/scripts/run_full_stack.sh --rebuild --logs
```

This runs everything in Docker (web, api, worker, Postgres, Redis, MinIO) with the `full` Compose profile.

- Stop: `./infra/scripts/stop_full_stack.sh` (add `--prune` to drop volumes/data)
- Logs: add `--logs` to the start command to stream logs in the same terminal, or run `docker compose -f infra/docker/docker-compose.yml --profile full logs -f`

### One command (local dev helpers)

```bash
git clone https://github.com/yourusername/slide2anki.git
cd slide2anki
./infra/scripts/dev.sh
```

This starts Postgres, Redis, and MinIO in Docker. Run the API/worker/web locally per the guidance printed by the script, or pass `--docker` to also run API and worker in containers.

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
uv sync
uv run uvicorn app.main:app --reload

# Run the worker (in another terminal)
cd workers/runner
uv sync
uv run python -m runner.worker
```

## Configuration

### Model provider settings (recommended)

Configure the model provider in the web UI:

1. Open `http://localhost:3000/settings`
2. Select `OpenRouter` (or another provider) + a model
3. Enter the provider API key
4. Click **Save Settings**

These settings are stored in the local Postgres container so the worker can read them. The UI masks API keys after saving.

To wipe local secrets + data, run `./infra/scripts/reset_db.sh` (this removes the Docker volumes).

### Optional `.env` (only needed for local, non-Docker runs)

If you run the API/worker outside Docker, create a `.env` file in the root directory:

```env
POSTGRES_URL=postgresql+asyncpg://slide2anki:slide2anki@localhost:5432/slide2anki
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
API_INTERNAL_URL=http://api:8000   # for Docker SSR; browser uses NEXT_PUBLIC_API_URL
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

cd packages/core && uv run pytest
cd apps/api && uv run pytest
cd apps/web && npm test
```

### Regenerate the API client

```bash
./tools/generate_openapi_client.sh
```

## Roadmap

Completed:

- PDF upload and rendering
- Basic card generation pipeline
- Review UI with evidence highlighting
- TSV export
- APKG export with embedded images
- Model provider configuration (OpenRouter, Ollama)

Planned:

- Batch processing improvements
- Asset masking for diagram-based cards
- User authentication and multi-tenancy
- Deployed web version with accounts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Source Available - Personal use only. See [LICENSE](LICENSE) for details.
