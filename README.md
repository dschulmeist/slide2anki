# slide2anki

A sophisticated document-to-flashcard pipeline powered by **multi-agent LangGraph orchestration**. slide2anki transforms lecture PDFs into high-quality Anki flashcards using hierarchical graph-based agents, with every card traceable to its visual source evidence.

## Key Features

- **Multi-Agent Pipeline**: Hierarchical LangGraph agents for extraction, generation, and quality control
- **Vision-First Processing**: Treats slides as visual documents, preserving diagrams, formulas, and layout
- **Intelligent Optimization**: Automatic text-only page detection saves 30-60% on API costs
- **Fault-Tolerant Execution**: PostgreSQL-backed checkpointing enables job resumption after failures
- **Evidence Traceability**: Every flashcard links back to the exact slide region it came from
- **Provider Agnostic**: Supports OpenAI GPT-5.x, Google Gemini 3, xAI Grok 4, Claude 4.5, and local Ollama models

---

<table>
  <tr>
    <td><img alt="Projects view" src="https://github.com/user-attachments/assets/9aea863d-6994-4ae3-9add-2e4b336b492e" /></td>
    <td><img alt="Card review" src="https://github.com/user-attachments/assets/d1aea906-9e2f-4f72-a8fd-1638b0365835" /></td>
  </tr>
</table>

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              slide2anki                                     │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│   Web UI    │   FastAPI   │   Worker    │   Core      │   Infrastructure    │
│  (Next.js)  │   (API)     │  (Jobs)     │ (LangGraph) │                     │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────────────┤
│ React 18    │ SQLAlchemy  │ Redis Queue │ Multi-Agent │ PostgreSQL 16       │
│ TypeScript  │ Pydantic 2  │ Checkpoint  │ Pipelines   │ Redis 7             │
│ Tailwind    │ AsyncIO     │ Progress    │ Adapters    │ MinIO S3            │
│ Zustand     │ SSE Stream  │ Retry       │ Schemas     │ Docker Compose      │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
```

### Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Web UI** | Next.js 14, React 18, Tailwind, Zustand | User interface for uploads, review, settings |
| **API** | FastAPI, SQLAlchemy, asyncpg | REST endpoints, request validation, job dispatch |
| **Queue** | Redis + RQ | Decouples long-running tasks from HTTP requests |
| **Worker** | Python worker process | Executes pipeline jobs, manages checkpoints |
| **Postgres** | PostgreSQL 16 | Stores projects, documents, markdown, cards, jobs, checkpoints |
| **MinIO** | S3-compatible storage | Stores PDFs, slide images, exports |
| **Core** | LangGraph, Pydantic | Framework-agnostic multi-agent extraction and generation |

---

## LangGraph Multi-Agent System

The core of slide2anki is a **hierarchical multi-agent system** built with LangGraph. This architecture enables complex document processing through composable, fault-tolerant graph execution.

### Agent Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        build_markdown_graph (Orchestrator)                   │
│  Coordinates the full PDF → Markdown pipeline                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────────────┐    ┌──────────┐          │
│   │ ingest  │───▶│ render  │───▶│  slide_worker   │───▶│ markdown │          │
│   │  node   │    │  node   │    │   (parallel)    │    │   node   │          │
│   └─────────┘    └─────────┘    └────────┬────────┘    └──────────┘          │
│                                          │                                   │
│                         ┌────────────────┼────────────────┐                  │
│                         ▼                ▼                ▼                  │
│                  ┌────────────┐   ┌────────────┐   ┌────────────┐            │
│                  │   Slide    │   │   Slide    │   │   Slide    │            │
│                  │  Worker 1  │   │  Worker 2  │   │  Worker N  │            │
│                  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘            │
│                        │                │                │                   │
└────────────────────────┼────────────────┼────────────────┼───────────────────┘
                         │                │                │
           ┌─────────────┴────────────────┴────────────────┴─────────────┐
           │                    build_slide_graph                        │
           │  Per-slide extraction with region-aware processing          │
           ├─────────────────────────────────────────────────────────────┤
           │                                                             │
           │   ┌─────────┐    ┌─────────────────┐                        │
           │   │ segment │───▶│  region_worker  │                        │
           │   │  node   │    │   (parallel)    │                        │
           │   └─────────┘    └────────┬────────┘                        │
           │                           │                                 │
           │          ┌────────────────┼────────────────┐                │
           │          ▼                ▼                ▼                │
           │   ┌────────────┐   ┌────────────┐   ┌────────────┐          │
           │   │  Region    │   │  Region    │   │  Region    │          │
           │   │  Worker 1  │   │  Worker 2  │   │  Worker N  │          │
           │   └────────────┘   └────────────┘   └────────────┘          │
           │                                                             │
           └─────────────────────────────────────────────────────────────┘
                                        │
           ┌────────────────────────────┴─────────────────────────────────┐
           │                    build_region_graph                        │
           │  Extract, verify, and repair claims from a single region     │
           ├──────────────────────────────────────────────────────────────┤
           │                                                              │
           │   ┌─────────────┐    ┌────────────┐    ┌────────────┐        │
           │   │   extract   │───▶│   verify   │───▶│   repair   │        │
           │   │   region    │    │   claims   │    │   claims   │<------││
           │   └─────────────┘    └────────────┘    └─────┬──────┘       ││
           │                                              │ (retry loop) |│
           │                                              └──────────────|│
           └──────────────────────────────────────────────────────────────┘
```

### Graph Definitions

| Graph | Purpose | Nodes | Concurrency |
|-------|---------|-------|-------------|
| `build_markdown_graph` | Orchestrates PDF → Markdown extraction | ingest → render → slide_worker → markdown | Slides processed in parallel |
| `build_slide_graph` | Per-slide segmentation and extraction | config → segment → region_worker | Regions processed in parallel |
| `build_region_graph` | Claim extraction with quality control | extract → verify → repair (loop) | Sequential with retry |
| `build_card_graph` | Markdown → Flashcards generation | write_cards → critique → repair → dedupe | Sequential pipeline |

### State Management

Each graph maintains typed state using Pydantic models with **reducer functions** for parallel aggregation:

```python
class MarkdownPipelineState(TypedDict, total=False):
    pdf_data: bytes                                    # Input PDF
    document: Document                                 # Parsed document
    slides: list[Slide]                               # Rendered pages
    claims: Annotated[list[Claim], _merge_claims]     # Aggregated claims (reducer)
    markdown_blocks: list[MarkdownBlock]              # Output blocks
    errors: list[str]                                 # Error accumulator

def _merge_claims(existing: list[Claim], incoming: list[Claim]) -> list[Claim]:
    """Reducer: Combines claims from parallel slide workers."""
    return [*existing, *incoming] if existing else list(incoming or [])
```

The `Annotated[list[Claim], _merge_claims]` pattern enables **fan-out/fan-in parallelism**: multiple slide workers run concurrently, and their claim lists are automatically merged.

### Conditional Routing with Send API

LangGraph's `Send` API enables dynamic parallelism based on runtime state:

```python
def _dispatch_slides(state: MarkdownPipelineState) -> list[Send]:
    """Fan-out: Send each slide to a parallel worker."""
    slides = state.get("slides", [])
    return [Send("slide_worker", {"slide": slide}) for slide in slides]

# In graph construction:
graph.add_conditional_edges("render", _dispatch_slides)
```

This pattern is used at two levels:
1. **Slide dispatch**: After rendering, each slide is sent to its own `slide_worker` subgraph
2. **Region dispatch**: After segmentation, each region is sent to its own `region_worker` subgraph

---

## Pipeline Deep Dive

### Phase 1: Document Ingestion & Rendering

```
PDF Upload → Validation → Page Rendering → Text-Only Detection
```

**Key Innovation: Intelligent Text-Only Detection**

Before processing, each page is analyzed to determine if it's text-only:

```python
def _analyze_page_content(pdf_data: bytes) -> list[tuple[bool, str | None]]:
    """Analyze PDF pages to detect text-only pages and extract text."""
    with pdfplumber.open(BytesIO(pdf_data)) as pdf:
        for page in pdf.pages:
            # Calculate meaningful image area (excluding small icons < 50px)
            meaningful_image_area = sum(
                w * h for img in page.images
                if (w := img["x1"] - img["x0"]) > 50 and (h := img["bottom"] - img["top"]) > 50
            )

            # Text-only if images cover < 5% of page
            is_text_only = (meaningful_image_area / page_area) < 0.05

            if is_text_only:
                extracted_text = page.extract_text()  # Direct PDF text extraction
```

**Benefits:**
- **30-60% cost reduction**: Text-only pages skip the vision model entirely
- **Faster processing**: Text extraction is ~10x faster than vision inference
- **Same quality**: Extracted text feeds into the same claim extraction prompts

### Phase 2: Hierarchical Extraction

```
Slide → Segment (Vision) → Regions → Extract Claims (Vision/Text) → Verify → Repair
```

**Segmentation** identifies semantic regions on each slide:

```python
SEGMENT_PROMPT = """Segment this slide into labeled regions.
Return a JSON object with a "regions" array. Each region must include:
- kind: title, bullets, table, equation, diagram, image, or other
- bbox: normalized coordinates (0-1)
- confidence: 0-1 confidence score
"""
```

**Region Types:**

| Kind | Processing Strategy |
|------|-------------------|
| `title` | Extract as section header |
| `bullets` | Extract each bullet as potential claim |
| `table` | Structured data extraction |
| `equation` | LaTeX formula extraction |
| `diagram` | Visual relationship extraction |
| `image` | Caption/context extraction |

**Claim Extraction** adapts to content type:

```python
# For pages with meaningful images → Vision model
response = await adapter.extract_claims(
    image_data=region_image,
    prompt=EXTRACT_REGION_PROMPT,
)

# For text-only pages → Text model (cheaper, faster)
if slide.is_text_only and slide.extracted_text:
    prompt = EXTRACT_TEXT_PROMPT.format(text=slide.extracted_text)
    response = await adapter.generate_structured(prompt=prompt)
```

### Phase 3: Quality Control Loop

```
Claims → Verify → [Invalid?] → Repair → Verify → [Still Invalid?] → Discard
                                  ↑__________________|
                                     (max 2 attempts)
```

The `build_region_graph` implements a **self-healing extraction loop**:

1. **Verify**: Check claims against quality criteria (specificity, evidence, format)
2. **Repair**: LLM rewrites invalid claims with specific feedback
3. **Retry**: Up to `max_claim_repairs` attempts (default: 2)

### Phase 4: Markdown Synthesis

Claims are deduplicated and organized into canonical markdown blocks:

```python
class MarkdownBlock(BaseModel):
    anchor_id: str      # Content-based hash for deduplication
    kind: str           # definition, fact, process, etc.
    content: str        # Markdown-formatted content
    evidence: list[Evidence]  # Source slide regions
    position_index: int # Ordering within chapter
```

**Deduplication Strategy:**
- Content is normalized (whitespace, casing)
- SHA-256 hash generates `anchor_id`
- Duplicate blocks merge their evidence lists (preserving all sources)

---

## Fault Tolerance & Checkpointing

### PostgreSQL-Backed State Persistence

slide2anki uses `langgraph-checkpoint-postgres` to persist graph state after each node execution:

```python
from langgraph.checkpoint.postgres import PostgresSaver

with get_checkpointer() as checkpointer:
    graph = build_markdown_graph(adapter, checkpointer=checkpointer)

    result = await graph.ainvoke(
        {"pdf_data": pdf_data},
        config={"configurable": {"thread_id": job_id}}  # Job ID = Thread ID
    )
```

**How It Works:**

1. **Before each node**: Current state is loaded from PostgreSQL
2. **After each node**: Updated state is persisted with the node name
3. **On failure**: Job can be retried, resuming from the last successful node
4. **Thread isolation**: Each job has its own checkpoint stream (keyed by `job_id`)

### Job Resume Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   ingest    │────▶│   render    │────▶│   slide_    │──X──│  markdown   │
│     ✓       │     │     ✓       │     │   worker    │     │   (fail)    │
└─────────────┘     └─────────────┘     └──────┬──────┘     └─────────────┘
                                               │
                    Checkpoint saved ──────────┘

                    ─── Job Retry ───
                                               │
                                               ▼
                                        ┌─────────────┐     ┌─────────────┐
                                        │   slide_    │────▶│  markdown   │
                                        │   worker    │     │     ✓       │
                                        │  (resume)   │     └─────────────┘
                                        └─────────────┘
```

**API Endpoint:**

```http
POST /api/v1/jobs/{job_id}/retry

# Response
{
  "id": "397ab870-389e-446e-bf95-bd6d6e519fbd",
  "status": "pending",
  "progress": 0,
  "current_step": "queued"
}
```

---

## Model Provider Abstraction

The `BaseModelAdapter` interface enables provider-agnostic LLM calls:

```python
class BaseModelAdapter(ABC):
    @abstractmethod
    async def extract_claims(self, image_data: bytes, prompt: str) -> list[dict]:
        """Vision model: Extract claims from slide image."""

    @abstractmethod
    async def generate_structured(self, prompt: str, image_data: bytes | None) -> dict | list:
        """Text/Vision model: Generate structured JSON output."""

    @abstractmethod
    async def generate_cards(self, claims: list[Claim], prompt: str) -> list[dict]:
        """Text model: Generate flashcard drafts from claims."""

    @abstractmethod
    async def critique_cards(self, cards: list[CardDraft], prompt: str) -> list[dict]:
        """Text model: Quality critique of flashcard drafts."""
```

### Supported Providers

| Provider | Adapter | Models | Use Case |
|----------|---------|--------|----------|
| **OpenAI** | `OpenAIAdapter` | GPT-5.2, GPT-5.1, GPT-5-mini, GPT-5-nano | Production, flagship quality |
| **Google** | `GoogleAdapter` | Gemini 3 Pro/Flash Preview, Gemini 2.5 | Cost-effective, 1M context |
| **xAI** | `XAIAdapter` | Grok 4.1 Fast, Grok 4 Fast | 2M context window |
| **OpenRouter** | `OpenAIAdapter` | Any OpenRouter model | Multi-provider access |
| **Ollama** | `OllamaAdapter` | LLaVA, Llama 3.3, Qwen 2.5 | Local, privacy-focused |

### Automatic Fallbacks

Adapters handle provider-specific quirks automatically:

```python
# OpenAI: Handle max_tokens vs max_completion_tokens
if _uses_max_completion_tokens(model):  # GPT-5.x, o-series models
    create_kwargs["max_completion_tokens"] = 4096
else:
    create_kwargs["max_tokens"] = 4096

# Google: Handle empty responses gracefully
if not response.candidates or not candidate.content.parts:
    logger.warning(f"No content in response (finish_reason={finish_reason})")
    return ""  # Graceful degradation instead of crash

# xAI: Uses OpenAI-compatible API with rate limit handling
response = await client.chat.completions.create(
    model="grok-4-1-fast-non-reasoning",
    messages=messages,
    max_tokens=4096,
)
```

---

## Data Model

```
Project (workspace)
  ├── Document (uploaded PDF)
  │     └── Slide (rendered page image)
  │           ├── is_text_only: bool      # Optimization flag
  │           ├── extracted_text: str     # Pre-extracted for text-only pages
  │           └── Claim (extracted atomic fact)
  │                 └── Evidence (slide region bbox + snippet)
  ├── Chapter (document section)
  │     └── MarkdownBlock (canonical content unit)
  │           └── Evidence[] (source regions, merged on dedup)
  ├── MarkdownVersion (full snapshot for rollback)
  ├── Deck (flashcard collection)
  │     └── CardDraft (generated card)
  │           └── CardRevision (edit history)
  ├── GenerationConfig (card generation settings)
  └── Job (async task)
        ├── JobEvent[] (progress log)
        └── Checkpoint (LangGraph state, in postgres)
```

---

## Request Lifecycle

```
┌──────┐  Upload   ┌─────┐  Enqueue   ┌───────┐  Process   ┌──────────┐
│ User │─────────▶│ API │───────────▶│ Redis │───────────▶│  Worker  │
└──────┘   PDF    └─────┘   Job      └───────┘            └────┬─────┘
                     │                                         │
                     │ Store PDF                               │ Run Graph
                     ▼                                         ▼
                ┌─────────┐                            ┌──────────────┐
                │  MinIO  │                            │  LangGraph   │
                └─────────┘                            │   Pipeline   │
                                                       └──────┬───────┘
                     │                                        │
                     │ Store slides                           │ Checkpoint
                     ▼                                        ▼
                ┌─────────┐    Persist results         ┌──────────────┐
                │  MinIO  │◀───────────────────────────│  PostgreSQL  │
                └─────────┘                            └──────────────┘
                                                              │
                     ┌────────────────────────────────────────┘
                     ▼
                ┌─────────┐  Stream    ┌─────┐  Display  ┌──────┐
                │  Redis  │───────────▶│ API │──────────▶│ User │
                └─────────┘  Progress  └─────┘   SSE     └──────┘
```

### Detailed Steps

1. **Upload**: User uploads PDF via Web UI
2. **Store**: API stores PDF in MinIO, creates `Document` record
3. **Enqueue**: API creates `Job` record, enqueues to Redis
4. **Dequeue**: Worker picks up job from Redis queue
5. **Process**: Worker runs `build_markdown_graph` with checkpointing
6. **Checkpoint**: State persisted to PostgreSQL after each node
7. **Progress**: Worker publishes progress to Redis pub/sub
8. **Stream**: API streams progress to UI via Server-Sent Events
9. **Persist**: Worker saves slides (MinIO), claims, blocks (PostgreSQL)
10. **Complete**: Job marked complete, user can review/generate cards

---

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+
- A model provider API key

### Quick Start (Full Stack)

```bash
git clone https://github.com/yourusername/slide2anki.git
cd slide2anki
./infra/scripts/run_full_stack.sh --rebuild --logs
```

Open http://localhost:3000 and configure your model provider in Settings.

### Development Mode

```bash
# Start infrastructure only
./infra/scripts/dev.sh

# In separate terminals:
cd apps/web && npm install && npm run dev      # Frontend
cd apps/api && uv sync && uv run uvicorn app.main:app --reload  # API
cd workers/runner && uv sync && uv run python -m runner.worker  # Worker
```

### Configuration

Configure the model provider in the web UI at `/settings`:

| Provider | Base URL | Recommended Models |
|----------|----------|--------------------|
| OpenAI | (default) | gpt-5.2, gpt-5-mini (cost-effective) |
| Google | (default) | gemini-3-flash-preview, gemini-3-pro-preview |
| xAI | https://api.x.ai/v1 | grok-4-1-fast-non-reasoning |
| OpenRouter | https://openrouter.ai/api/v1 | Any model (includes free tiers) |
| Ollama | http://localhost:11434 | llava, llama3.3 |

---

## Project Structure

```
slide2anki/
├── apps/
│   ├── web/                    # Next.js 14 frontend
│   │   ├── app/               # App router pages
│   │   ├── components/        # React components
│   │   └── lib/               # API client, state
│   └── api/                    # FastAPI backend
│       ├── app/
│       │   ├── routers/       # API endpoints
│       │   ├── db/            # SQLAlchemy models
│       │   ├── services/      # Business logic
│       │   └── schemas/       # Pydantic schemas
│       └── alembic/           # Database migrations
├── packages/
│   └── core/                   # LangGraph pipeline (framework-agnostic)
│       └── slide2anki_core/
│           ├── graph/         # Graph builders and nodes
│           │   ├── build_markdown_graph.py
│           │   ├── build_slide_graph.py
│           │   ├── build_region_graph.py
│           │   ├── build_card_graph.py
│           │   └── nodes/     # Individual node implementations
│           ├── model_adapters/ # LLM provider adapters
│           ├── schemas/       # Pydantic models
│           └── utils/         # Helpers (retry, logging, PDF)
├── workers/
│   └── runner/                 # Background job worker
│       └── runner/
│           ├── tasks/         # Job implementations
│           ├── config.py      # Worker settings
│           └── worker.py      # RQ worker entry
└── infra/
    ├── docker/                # Docker Compose configs
    └── scripts/               # Dev scripts
```

---

## Tech Stack

### Backend
- **Python 3.11+** - Type hints, async/await
- **FastAPI** - High-performance async API framework
- **SQLAlchemy 2.0** - Async ORM with type safety
- **LangGraph** - Graph-based agent orchestration
- **Pydantic 2** - Data validation and serialization
- **Redis + RQ** - Job queue with pub/sub progress
- **PostgreSQL 16** - Primary database + checkpoint storage
- **MinIO** - S3-compatible object storage

### Frontend
- **Next.js 14** - React framework with App Router
- **React 18** - UI components with hooks
- **TypeScript** - Type-safe frontend code
- **Tailwind CSS** - Utility-first styling
- **Zustand** - Lightweight state management
- **SWR** - Data fetching with caching

### Infrastructure
- **Docker Compose** - Local development environment
- **Alembic** - Database migrations

---

## Roadmap

### Completed

- [x] Multi-agent LangGraph pipeline
- [x] Vision-based slide extraction
- [x] Text-only page optimization
- [x] PostgreSQL checkpointing for job resume
- [x] Multiple model provider support
- [x] Real-time progress streaming (SSE)
- [x] APKG export with embedded images
- [x] Evidence-linked card review UI

### Planned

- [ ] Batch document processing
- [ ] Diagram-specific card generation
- [ ] Formula rendering in cards (MathJax/KaTeX)
- [ ] User authentication and multi-tenancy
- [ ] Cloud deployment with accounts
- [ ] Spaced repetition study mode

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Source Available - Personal use only. See [LICENSE](LICENSE) for details.
