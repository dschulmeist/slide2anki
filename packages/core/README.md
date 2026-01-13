# slide2anki-core

Core pipeline for converting lecture slides to Anki flashcards.

## Overview

This package contains the LangGraph-based pipeline that processes PDF documents
into structured markdown and flashcards. It supports two processing modes:

### Holistic Pipeline (Default)

The recommended approach that processes documents as coherent units:

1. Renders PDF pages to images with text-only detection
2. Extracts and classifies images (formulas, diagrams, charts, code, tables)
3. Transcribes images (formulas to LaTeX, code to code blocks, tables to markdown)
4. Processes documents in overlapping chunks (15% overlap) for context continuity
5. Detects chapters from content structure
6. Assembles clean, deduplicated markdown
7. Generates flashcards from the markdown

### Legacy Pipeline

Per-slide extraction with region segmentation. Available by setting
`use_holistic_pipeline=False`. May produce redundant content on metadata-heavy
documents.

## Installation

```bash
# Using uv
uv pip install -e .

# With Ollama support
uv pip install -e ".[ollama]"

# With dev dependencies
uv pip install -e ".[dev]"
```

## Usage

### Holistic Pipeline (Recommended)

```python
from slide2anki_core import build_holistic_graph, HolisticConfig
from slide2anki_core.model_adapters import OpenAIAdapter

# Create model adapter
adapter = OpenAIAdapter(api_key="sk-...")

# Configure the holistic pipeline
config = HolisticConfig(
    chunk_size=10,           # Process 10 slides per chunk
    chunk_overlap=0.15,      # 15% overlap between chunks
    extract_images=True,     # Extract and process images
    transcribe_formulas=True,  # Convert formula images to LaTeX
    describe_diagrams=True,  # Generate descriptions for diagrams
    detect_chapters=True,    # Detect chapter structure
)

# Build the pipeline graph
graph = build_holistic_graph(adapter, config=config)

# Run the pipeline
result = await graph.ainvoke({
    "pdf_data": pdf_bytes,
    "deck_name": "Biology 101",
})

# Access results
markdown = result["markdown_content"]
blocks = result["markdown_blocks"]
```

### Legacy Pipeline

```python
from slide2anki_core import build_markdown_graph
from slide2anki_core.model_adapters import OpenAIAdapter

adapter = OpenAIAdapter(api_key="sk-...")
graph = build_markdown_graph(adapter)

result = await graph.ainvoke({
    "pdf_path": "lecture.pdf",
    "deck_name": "Biology 101",
})
```

### Card Generation

```python
from slide2anki_core import build_card_graph

# Build card generation graph
card_graph = build_card_graph(adapter)

# Generate cards from markdown
result = await card_graph.ainvoke({
    "markdown_content": markdown,
    "deck_name": "Biology 101",
})

for card in result["cards"]:
    print(f"Q: {card.front}")
    print(f"A: {card.back}")
```

## Pipeline Stages

### Holistic Pipeline

```
ingest -> render -> extract_images -> classify_images -> transcribe_images
       -> extract_document -> detect_chapters -> assemble_markdown
```

| Stage | Purpose |
|-------|---------|
| **ingest** | Load PDF and validate |
| **render** | Convert pages to images, detect text-only pages |
| **extract_images** | Extract images from slides, filter branding/logos |
| **classify_images** | Classify as formula, diagram, chart, code, table, etc. |
| **transcribe_images** | Convert formulas to LaTeX, code to blocks, tables to markdown |
| **extract_document** | Process document in overlapping chunks for coherent markdown |
| **detect_chapters** | Identify chapter structure from content |
| **assemble_markdown** | Combine chunks, deduplicate, organize by chapter |

### Image Processing

Images are intelligently processed based on their type:

| Image Type | Processing |
|------------|------------|
| **Formula** | Transcribed to LaTeX (`$$E = mc^2$$`) |
| **Code** | Transcribed to code blocks with language detection |
| **Table** | Converted to markdown table format |
| **Diagram** | Described in text, optionally embedded |
| **Chart** | Described with key data points |
| **Photo** | Described contextually |
| **Logo/Decorative** | Filtered out (header/footer detection) |

### Image Filtering

Images are automatically filtered based on:

- **Position**: Images in header (top 15%) or footer (bottom 15%) are likely branding
- **Size**: Images smaller than 5% of slide area are likely icons
- **Repetition**: Images appearing on >50% of slides are likely logos

## Model Adapters

The pipeline supports multiple model backends:

- **OpenAI**: GPT-4 Vision for extraction, GPT-4 for writing/critique
- **Google**: Gemini models with vision support
- **xAI**: Grok models with large context windows
- **Ollama**: Local models like LLaVA for vision, Llama for text

## Schemas

All data structures are defined with Pydantic for validation and serialization:

### Core Schemas

- `Document`: Represents the input PDF
- `Slide`: A rendered page with optional extracted text
- `Claim`: An extracted piece of knowledge
- `MarkdownBlock`: A unit of markdown content with evidence

### Image Schemas

- `ImagePosition`: Normalized position (0-1) with area/center calculations
- `ImageType`: Classification enum (formula, diagram, chart, code, etc.)
- `ExtractedImage`: Raw image with position and occurrence count
- `ProcessedImage`: Classified image with transcription/description

### Chapter Schemas

- `Chapter`: A document section with title and slide range
- `ChapterOutline`: Full chapter structure
- `DocumentChunk`: A chunk of slides for processing
- `ChunkingConfig`: Configuration for chunk creation

## Configuration

### HolisticConfig

```python
@dataclass(frozen=True)
class HolisticConfig:
    # Chunking
    chunk_size: int = 10           # Slides per chunk
    chunk_overlap: float = 0.15    # Overlap ratio between chunks

    # Image filtering
    header_threshold: float = 0.15  # Top % considered header
    footer_threshold: float = 0.15  # Bottom % considered footer
    min_image_area: float = 0.05    # Minimum image size (% of slide)
    repetition_threshold: float = 0.5  # Max repetition before filtering

    # Feature flags
    extract_images: bool = True
    transcribe_formulas: bool = True
    describe_diagrams: bool = True
    embed_complex_images: bool = True
    detect_chapters: bool = True
    use_toc_if_present: bool = True
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=slide2anki_core

# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy slide2anki_core
```

## Architecture

The holistic pipeline addresses issues with per-slide extraction:

1. **Natural deduplication**: Metadata (dates, presenter names) mentioned once
2. **Context preservation**: Understands relationships between slides
3. **Better quality**: Model sees the whole picture
4. **Fewer API calls**: One call per chunk instead of per-region
5. **Smart image handling**: Formulas transcribed, logos filtered

The chunking strategy with 15% overlap ensures context continuity across
chunk boundaries while keeping individual API calls manageable.
