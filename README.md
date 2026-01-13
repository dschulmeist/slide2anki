# slide2anki

A sophisticated document-to-flashcard pipeline powered by **multi-agent LangGraph orchestration**. slide2anki transforms lecture PDFs into high-quality Anki flashcards using hierarchical graph-based agents, with every card traceable to its visual source evidence.

## Key Features

- **Holistic Document Processing**: Processes documents as coherent units with 15% overlapping chunks for context continuity
- **Smart Image Handling**: Extracts images, classifies them (formula, diagram, code, table), and transcribes to appropriate formats
- **Vision-First Processing**: Treats slides as visual documents, preserving diagrams, formulas, and layout
- **Natural Deduplication**: Metadata and repeated content handled once, not per-slide
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

### Pipeline Modes

slide2anki supports two extraction pipelines:

**Holistic Pipeline (Default)**: Processes documents as coherent units with overlapping chunks. Produces higher quality output with natural deduplication and context preservation.

**Legacy Pipeline**: Per-slide extraction with region segmentation. Available as fallback for specific use cases.

### Holistic Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     build_holistic_graph (Orchestrator)                      │
│  Processes documents as coherent units with smart image handling             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌──────────────┐          │
│   │ ingest  │───▶│ render  │───▶│  extract    │───▶│   classify   │          │
│   │  node   │    │  node   │    │   images    │    │    images    │          │
│   └─────────┘    └─────────┘    └─────────────┘    └──────┬───────┘          │
│                                                           │                  │
│   ┌───────────────────────────────────────────────────────┘                  │
│   │                                                                          │
│   ▼                                                                          │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐  │
│   │ transcribe  │───▶│  extract    │───▶│   detect    │───▶│   assemble   │  │
│   │   images    │    │  document   │    │  chapters   │    │   markdown   │  │
│   └─────────────┘    └──────┬──────┘    └─────────────┘    └──────────────┘  │
│                             │                                                │
│          ┌──────────────────┼──────────────────┐                             │
│          ▼                  ▼                  ▼                             │
│   ┌────────────┐     ┌────────────┐     ┌────────────┐                       │
│   │  Chunk 1   │     │  Chunk 2   │     │  Chunk N   │  (15% overlap)        │
│   │ slides 1-10│     │ slides 9-18│     │slides N-M  │                       │
│   └────────────┘     └────────────┘     └────────────┘                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Image Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Image Processing Flow                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Extract Images                    Classify Images                         │
│   ┌────────────────────────┐       ┌────────────────────────────┐           │
│   │ - Position detection   │──────▶│ - Formula detection        │           │
│   │ - Size filtering       │       │ - Diagram identification   │           │
│   │ - Repetition counting  │       │ - Code/table recognition   │           │
│   │ - Header/footer filter │       │ - Logo/decorative filter   │           │
│   └────────────────────────┘       └─────────────┬──────────────┘           │
│                                                  │                          │
│                                                  ▼                          │
│                                    Transcribe Images                        │
│                                    ┌────────────────────────────┐           │
│                                    │ Formula → LaTeX ($$...$$)  │           │
│                                    │ Code    → Code blocks      │           │
│                                    │ Table   → Markdown table   │           │
│                                    │ Diagram → Description      │           │
│                                    └────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Graph Definitions

| Graph | Purpose | Nodes | Mode |
|-------|---------|-------|------|
| `build_holistic_graph` | Document-level extraction with chunking | ingest → render → images → extract → chapters → assemble | Default |
| `build_markdown_graph` | Legacy per-slide extraction | ingest → render → slide_worker → markdown | Fallback |
| `build_slide_graph` | Per-slide segmentation (legacy) | config → segment → region_worker | Legacy |
| `build_region_graph` | Region claim extraction (legacy) | extract → verify → repair (loop) | Legacy |
| `build_card_graph` | Markdown → Flashcards generation | write_cards → critique → repair → dedupe | Both modes |

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
- **Same quality**: Extracted text feeds into the same extraction prompts

### Phase 2: Holistic Document Extraction (Default)

```
Document → Chunking (15% overlap) → Extract per Chunk → Merge → Deduplicate
```

The holistic pipeline processes documents as coherent units rather than per-slide:

**Chunking Strategy:**

```python
class ChunkingConfig(BaseModel):
    target_chunk_size: int = 10      # Slides per chunk
    overlap_ratio: float = 0.15      # 15% overlap between chunks
    min_chunk_size: int = 3
    max_chunk_size: int = 20

    def create_chunks(self, total_slides: int) -> list[DocumentChunk]:
        """Create overlapping chunks for context continuity."""
```

**Benefits over per-slide extraction:**

| Aspect | Per-Slide (Legacy) | Holistic (Default) |
|--------|-------------------|-------------------|
| Metadata handling | Repeated per slide | Mentioned once |
| Context | Isolated | Preserved across slides |
| API calls | Per region (~50+) | Per chunk (~2-4) |
| Deduplication | Post-processing | Natural |
| Quality | Variable | Consistent |

**Image Processing:**

Images are extracted, classified, and transcribed intelligently:

| Image Type | Detection | Processing |
|------------|-----------|------------|
| **Formula** | Math symbols, equation layout | Transcribed to LaTeX (`$$E=mc^2$$`) |
| **Code** | Syntax patterns, monospace | Transcribed to code blocks |
| **Table** | Grid structure | Converted to markdown table |
| **Diagram** | Shapes, arrows, flowcharts | Described in text |
| **Logo** | Header/footer, repetition | Filtered out |
| **Decorative** | Small size, edges | Filtered out |

**Image Filtering Rules:**

```python
# Filter images based on position, size, and repetition
header_threshold: float = 0.15   # Top 15% = likely branding
footer_threshold: float = 0.15   # Bottom 15% = likely branding
min_image_area: float = 0.05     # < 5% of slide = likely icon
repetition_threshold: float = 0.5  # > 50% of slides = likely logo
```

### Phase 3: Chapter Detection & Organization

```
Raw Markdown → Detect Headers → Build Chapter Outline → Organize Content
```

The pipeline detects chapter structure from:
- Table of contents slides
- Markdown headers in extracted content
- Topic transitions identified by the model

### Phase 4: Markdown Assembly

Content is deduplicated and organized into canonical markdown blocks:

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
│           │   ├── build_holistic_graph.py   # Default: document-level extraction
│           │   ├── build_markdown_graph.py   # Legacy: per-slide extraction
│           │   ├── build_card_graph.py       # Markdown → flashcards
│           │   ├── holistic/  # Holistic pipeline nodes
│           │   │   ├── extract_images.py     # Image extraction & filtering
│           │   │   ├── classify_images.py    # Image type classification
│           │   │   ├── transcribe_images.py  # Formula/code transcription
│           │   │   ├── extract_document.py   # Chunked document extraction
│           │   │   ├── detect_chapters.py    # Chapter structure detection
│           │   │   └── assemble_markdown.py  # Final markdown assembly
│           │   └── nodes/     # Legacy pipeline nodes
│           ├── model_adapters/ # LLM provider adapters
│           ├── schemas/       # Pydantic models
│           │   ├── images.py  # Image processing schemas
│           │   ├── chapters.py # Chapter and chunking schemas
│           │   └── ...        # Core schemas
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
- [x] Holistic document processing pipeline
- [x] Smart image extraction and classification
- [x] Formula transcription to LaTeX
- [x] Chapter detection and organization
- [x] Chunk-based processing with overlap

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
