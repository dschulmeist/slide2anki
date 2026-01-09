# slide2anki-core

Core pipeline for converting lecture slides to Anki flashcards.

## Overview

This package contains the LangGraph-based pipeline that:
1. Renders PDF pages to images
2. Extracts atomic claims using vision models
3. Generates flashcard drafts
4. Critiques and improves cards
5. Deduplicates similar cards
6. Exports to Anki-compatible formats

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

```python
from slide2anki_core import build_graph
from slide2anki_core.model_adapters import OpenAIAdapter

# Create model adapter
adapter = OpenAIAdapter(api_key="sk-...")

# Build the pipeline graph
graph = build_graph(adapter)

# Run the pipeline
result = await graph.ainvoke({
    "pdf_path": "lecture.pdf",
    "deck_name": "Biology 101",
})

# Access generated cards
for card in result["cards"]:
    print(f"Q: {card.front}")
    print(f"A: {card.back}")
```

## Pipeline Stages

### 1. Ingest
Load PDF and prepare for processing.

### 2. Render
Convert each page to a high-resolution image.

### 3. Extract
Use vision models to identify atomic claims (definitions, facts, processes).

### 4. Write Cards
Transform claims into focused flashcard drafts.

### 5. Critique
Evaluate cards for quality and suggest improvements.

### 6. Dedupe
Remove or merge duplicate/overlapping cards.

### 7. Export
Generate TSV or .apkg files.

## Model Adapters

The pipeline supports multiple model backends:

- **OpenAI**: GPT-4 Vision for extraction, GPT-4 for writing/critique
- **Ollama**: Local models like LLaVA for vision, Llama for text

## Schemas

All data structures are defined with Pydantic for validation and serialization:

- `Document`: Represents the input PDF
- `Claim`: An extracted piece of knowledge
- `CardDraft`: A generated flashcard
- `Evidence`: Source reference with bounding boxes

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check --fix .

# Type checking
uv run mypy slide2anki_core
```
