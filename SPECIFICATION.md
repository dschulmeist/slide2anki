# slide2anki Project Specification

This document captures the agreed product direction, workflow, and a technically grounded implementation plan for the next phases of slide2anki.

## Goals

- Make a "project" the top-level workspace that can contain many uploaded documents.
- Build a canonical, deduplicated markdown knowledge base per project.
- Generate one or more decks from that knowledge base, defaulting to one deck per chapter.
- Keep evidence traceability back to original slides and regions.
- Run locally without accounts, using user-provided model endpoints and keys.
- Allow user edits to the markdown and to cards, with version history.

## Key Decisions

- Markdown is the ground-truth representation of knowledge.
- Markdown is generated automatically but editable by the user.
- Card generation runs only when the user explicitly requests it.
- Chapters are inferred automatically (no manual outline step).
- Decks are per-chapter by default; multiple decks per project are supported.
- Ordering rule: first appearance wins; edits become authoritative; dedup merges and cites all evidence.

## System Overview (Target)

1. Ingest one or more documents into a project.
2. Extract structured content and render assets (images, formulas).
3. Build a canonical markdown document with anchors and metadata.
4. When requested, generate cards from selected chapters with custom instructions.
5. Review and edit cards with evidence and version history.
6. Export decks (TSV now, APKG later).

## Data Model (Proposed)

Project
- id, name, created_at, updated_at

Document
- id, project_id, filename, storage_key, created_at

MarkdownVersion
- id, project_id, version, content, created_at, created_by

MarkdownBlock
- id, project_id, anchor_id, chapter_id, type (text/formula/image)
- content, evidence_refs, position_index

Chapter
- id, project_id, title, position_index

Asset (Image)
- id, project_id, storage_key, media_type, width, height
- source_evidence (slide/page + bbox)

Mask
- id, asset_id, mask_type (rect), params (x,y,w,h)
- usage (front_only, back_only)

Deck
- id, project_id, chapter_id, title, status

CardDraft
- id, deck_id, anchor_id, front, back, tags, status
- evidence_refs, generation_config_id

CardRevision
- id, card_id, revision_number, front, back, tags, editor, created_at

GenerationConfig
- id, project_id, chapter_id, max_cards, focus (formulas/definitions/processes)
- custom_instructions, model_provider, model_name

## Technical Approach

### Pipeline (LangGraph)
- Ingest: render PDF to images (pdf2image).
- Extract: vision model identifies claims, formulas, and diagrams with bounding boxes.
- Normalize: map evidence to normalized coordinates; store anchors.
- Build Markdown:
  - Each block includes an anchor ID, evidence references, and structured metadata.
  - Formulas are stored in LaTeX.
  - Diagrams are stored as assets and embedded in markdown.
- Deduplicate:
  - Merge similar blocks; keep earliest ordering; attach multiple evidence refs.
  - Prefer user-edited content on subsequent merges.

### Backends
- API: FastAPI for project/doc/markdown/deck/card management.
- Queue: Redis list for pipeline tasks and SSE progress events.
- Storage: MinIO for PDFs, slide images, assets, and deck exports.
- DB: Postgres for metadata, blocks, chapters, cards, revisions.

### UI (Next.js + Tailwind)
- Project dashboard (documents, pipeline status).
- Markdown viewer/editor with structured navigation by chapter.
- Card generation wizard:
  - Select chapters, max cards, focus modes, custom instructions.
- Review UI:
  - Evidence overlay with masks.
  - Revision history and revert.
- Export UI:
  - TSV now, APKG later.

## Ordering and Dedup Reasoning

- Order by earliest appearance keeps documents predictable and avoids reshuffling.
- Dedup merges into a single canonical block with multiple evidence citations, preserving trust.
- User edits are authoritative and remain at their chosen position.

## Card Generation Flow

1. User selects chapters (default all) and options (max cards, focus).
2. System generates cards chapter-by-chapter.
3. Cards link back to markdown anchors and original evidence.
4. User reviews and edits; revisions are stored.
5. Export uses approved revisions only.

## Evidence, Diagrams, and Masks

- Diagrams are stored as assets and embedded in markdown.
- Cards can reference an asset with optional front-side masks.
- Masks are defined as editable shapes (rectangles first).
- Rendering pipeline produces:
  - Question image (mask applied)
  - Answer image (full)

## Incremental Updates

- New documents trigger a pipeline pass that appends or merges blocks.
- Re-runs do not overwrite user edits; they add evidence and suggest merges.
- Markdown versions are stored to support rollback and audits.

## Phased Implementation Plan

Phase 0: Data Model and Migrations
- Introduce Project, Document, Chapter, MarkdownVersion, MarkdownBlock, GenerationConfig, CardRevision.
- Update Deck and CardDraft to reference chapters and markdown anchors.
- Adopt Alembic for schema evolution and generate a baseline migration.

Phase 1: Project + Multi-Document Ingest
- Add Project and Document entities.
- Attach uploads to a project.
- Store rendered slide images in MinIO.

Phase 2: Markdown Builder
- Generate markdown blocks with anchors and evidence.
- Store MarkdownVersion and MarkdownBlock rows.

Phase 3: Card Generation from Markdown
- UI for chapter selection and options.
- Card generation uses blocks, not raw slides.

Phase 4: Review + Versioning
- Card edit history.
- Export based on approved revisions.

Phase 5: Asset Masking
- Add mask editor and front-side masking in exports.

## Risks and Mitigations

- Risk: Markdown as ground truth can drift from slide evidence.
  - Mitigation: preserve evidence refs and block anchors; show evidence links in UI.
- Risk: Automatic chapter detection can be noisy.
  - Mitigation: allow user edits and reordering; keep deterministic IDs.
- Risk: Dedup merges can hide nuance.
  - Mitigation: merge with citations, not deletion; present merge suggestions for review.

## Notes on the Current Prototype

The current prototype runs a slide-based pipeline and stores slides, claims, and cards. The spec above adds a new canonical markdown layer and reorganizes card generation as a derived, user-triggered step.


risiken die chagpt genannt hat:
2) Automatische Kapitel-Erkennung

Das ist der wackeligste Punkt.

Slides sind oft:
• inkonsistent betitelt
• visuell statt strukturell gegliedert
• mit Wiederholungen und Einschüben

Deine Mitigation („user edits, reorder, deterministic IDs“) ist gut, aber:

Mein Rat:
• Baue Kapitelerkennung als assistiven Vorschlag, nicht als harte Wahrheit
• UI sollte „Split chapter here“ und „Merge with previous“ als First-Class-Aktion haben

Technisch passt das, aber UX ist hier entscheidend.

3) Dedup auf Block-Ebene kann semantische Nuancen plattbügeln

Auch mit „merge with citations“:

Beispiel:
• Block A: „ATP is produced in mitochondria“
• Block B: „Most ATP is produced in mitochondria during oxidative phosphorylation“

Automatische Dedup-Logik könnte das zusammenziehen, obwohl didaktisch wichtig ist, dass „most“ und „mechanism“ separat sind.

Deine Mitigation ist gut, aber:
• Dedup sollte immer Vorschlag, nicht Auto-Commit sein
• UI sollte Merge-Entscheidung sichtbar machen

Sonst wird das System „zu clever“.