# ChemMon Wiki — Design Spec

**Date:** 2026-04-07
**Status:** Draft
**Author:** David Foster + Claude

## Purpose

A standalone LLM wiki for EFSA Chemical Monitoring reporting guidance following the same pattern as the FoodEx2 wiki. Users ask questions about ChemMon reporting and get grounded answers with citations from a maintained knowledge base.

This is a Q&A knowledge service, not a coding assistant. No candidate lists, no policy pack synthesis, no solver.

## Approach

Fork the FoodEx2 wiki repo (`Chili36/Foodex2_Wiki`). Strip out FoodEx2-specific content and endpoints. Adapt for the ChemMon domain.

## Source Documents

- **Immutable layer:** ChemMon annual reporting guidance PDFs (2025, 2026, future years)
- **Ongoing ingest:** EFSA official clarifications from the ChemMon reporting Teams channel
- **Out of scope:** SSD2 element catalogues (stay in Qdrant), DMT business rule code (rules extracted from guidance instead)

## Repo Structure

```
ChemMon_Wiki/
  chemmon_docs/            # Immutable source PDFs
  raw/chemmon-guidance/    # LLM-built topic pages (emerge during ingest)
  index.md                 # Content catalog with guiding principles
  log.md                   # Chronological ingest/maintenance record
  PROJECT_CONTEXT.md       # What this wiki is, why it exists
  README.md                # Repo orientation
  wiki_api/
    app.py                 # FastAPI endpoints
    page_selector.py       # AnthropicWikiPageSelector (reused from FoodEx2)
    answerer.py            # AnthropicChemMonAnswerer (new)
    wiki_store.py          # WikiStore (unchanged from FoodEx2)
    static/viewer.html     # Browser view
  tests/
  requirements.txt         # fastapi, anthropic, pyyaml, python-dotenv, pytest
  .env.example
  .gitignore
```

## API Surface

### Static Endpoints (carried over from FoodEx2)

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| GET | /wiki/index | Raw index.md |
| GET | /wiki/pages | Page catalog with titles and summaries |
| GET | /wiki/pages/{page_name} | Single wiki page |
| GET | /wiki/view | Browser-based wiki viewer |

### LLM-Driven Endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | /wiki/ask | Question in, grounded answer with citations out |

### Request Model

```json
{
  "question": "Do I need to add F33 for acrylamide if my base term already has an implicit legislative class?",
  "max_pages": 6
}
```

Fields:
- `question` (string, required): The user's question about ChemMon reporting
- `max_pages` (int, optional, default 6, range 1-10): Maximum wiki pages to retrieve

### Response Model

```json
{
  "answer": "Yes. CHEMMON12 requires explicit F33 for acrylamide regardless of...",
  "citations": ["domain-specific-validation.md", "chemical-monitoring-foodex2.md"],
  "pages_used": ["index.md", "domain-specific-validation.md", "chemical-monitoring-foodex2.md"],
  "pages": [
    {
      "page_name": "...",
      "title": "...",
      "summary": "...",
      "sources": [],
      "related": [],
      "content": "..."
    }
  ],
  "trace": {
    "selection_method": "service-owned llm page selector + answerer",
    "model": "...",
    "token_summary": {},
    "timing_summary": {}
  }
}
```

Fields:
- `answer` (string): Grounded answer derived from wiki pages
- `citations` (list[string]): Page names that support the answer
- `pages_used` (list[string]): All pages retrieved by the selector
- `pages` (list[PageSummary]): Page metadata and content
- `trace` (dict): Token usage, timing, model info for both LLM stages

## Internal Architecture

Two-stage LLM flow:

### Stage 1: Page Selector (reused from FoodEx2)

- Receives the question plus the `index.md` catalog
- Picks relevant wiki pages (up to `max_pages`)
- Uses tool-use to batch-read selected pages
- System prompt adapted for ChemMon: "You are the ChemMon wiki page selector. Choose pages relevant to the user's question about chemical monitoring reporting."

### Stage 2: Answerer (new)

- Receives the question plus the selected page contents
- Returns a grounded answer with citations to specific pages
- Single LLM call, no tool use
- System prompt: "You are the ChemMon wiki assistant. Answer the question using only the provided wiki pages. Cite which page each claim comes from. If the wiki doesn't cover the question, say so."

### What to keep from FoodEx2

- `WikiStore` — unchanged, handles page reading, normalization, catalog, guiding principles
- `AnthropicWikiPageSelector` — reused with adapted system prompt
- Static endpoints — unchanged
- `static/viewer.html` — unchanged
- Page reading/tool-use infrastructure in librarian.py — reused by page selector
- Test patterns — adapted for new endpoint

### What to drop from FoodEx2

- `AnthropicWikiLibrarian` — policy pack synthesis not needed
- `AnthropicFoodEx2Solver` — no solver endpoint
- All candidate models (`CandidateHint`, `CandidateTrimmed`, `SolveCandidate`)
- All FoodEx2-specific response models (`PolicyPackResponse`, `SolveResponse`, `PolicyPackBody`, `QueryClassification`, `CandidateFocus`, etc.)
- `policy.py` — no policy contract concept
- Policy contract Pydantic models (`ConstitutionRule`, `DecisionProcedureStep`, `BindingRule`, `TieBreakRule`, `AntiPattern`, `PolicyContract`)

### What to add

- `AnthropicChemMonAnswerer` — single LLM call, question + pages in, answer + citations out
- `AskRequest` / `AskResponse` Pydantic models
- `/wiki/ask` endpoint

## Ingest Process

Same manual, LLM-assisted process as FoodEx2:

1. Add ChemMon guidance PDFs to `chemmon_docs/`
2. LLM reads the PDFs and extracts durable rules into topic pages under `raw/chemmon-guidance/`
3. Topic pages emerge organically — no predefined structure
4. Update `index.md` with new pages
5. Log every ingest in `log.md` with date, source, and what was extracted
6. Teams clarifications ingested the same way: extract the durable rule, add to relevant topic page, log it

### Page Conventions (carried over from FoodEx2)

- YAML frontmatter with title, sources, related pages, last_updated
- Source citations inline (PDF page numbers or "EFSA clarification, reporting channel")
- Cross-page links via `[[page-name]]`
- Concise, scannable, topic-oriented
- Topic pages over document dumps

## Environment Configuration

```bash
ANTHROPIC_API_KEY=...
WIKI_SELECTOR_MODEL=claude-sonnet-4-6
WIKI_ANSWERER_MODEL=claude-sonnet-4-6
```

## Testing

- Health, index, page listing, page read endpoints — unit tests with no LLM
- `/wiki/ask` — mocked LLM tests verifying the two-stage flow
- Page selector and answerer — individual mocked unit tests

## What This Design Does NOT Cover

- Predefined topic page structure (pages emerge during ingest)
- Automated ingest pipeline (manual, same as FoodEx2)
- DMT integration (DMT calls the API, that's a DMT-side concern)
- Policy contract layer (can be added later if a decision procedure emerges)
- Solver endpoint (not applicable for Q&A)
