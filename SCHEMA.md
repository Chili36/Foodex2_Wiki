---
title: "Wiki Schema"
last_updated: "2026-05-23"
sources:
  - "PROJECT_CONTEXT.md"
  - "KNOWLEDGE_ARCHITECTURE.md"
  - "INGEST_WORKFLOW.md"
  - "README.md"
related:
  - "[[KNOWLEDGE_ARCHITECTURE]]"
  - "[[PROJECT_CONTEXT]]"
  - "[[INGEST_WORKFLOW]]"
  - "[[MAINTENANCE_WORKFLOW]]"
  - "[[RUNTIME_RULES]]"
  - "[[policy-contract]]"
---

# Wiki Schema

This file defines the page types, frontmatter, and section conventions for the FoodEx2 wiki.

It exists so ingest passes stay consistent and so external callers can understand what kind of page they are looking at.

## Layer Model

The repo has four practical layers:

1. `foodex2_docs/`: immutable source material
2. `raw/efsa-guidance/`: compiled markdown knowledge pages
3. root runtime and maintenance docs such as `RUNTIME_RULES.md`, `MAINTENANCE_WORKFLOW.md`, `README.md`, and this file
4. `wiki_api/`: retrieval and serving layer

Do not write generated interpretations back into `foodex2_docs/`.
Do not move canonical policy or runtime guidance into service code when it can live as markdown.

## Page Types

### Orientation

Examples:

- `README.md`
- `PROJECT_CONTEXT.md`
- `KNOWLEDGE_ARCHITECTURE.md`
- `INGEST_WORKFLOW.md`
- `MAINTENANCE_WORKFLOW.md`
- `SCHEMA.md`

Use for:

- repo purpose
- architecture
- retrieval and knowledge-layer architecture decisions
- ingest method
- maintenance conventions
- deterministic and LLM-assisted wiki health checks

### Runtime

Examples:

- `RUNTIME_RULES.md`
- `policy-contract.md`

Use for:

- prompt-facing execution order
- always-on rules attached by retrieval
- compact runtime guidance for external callers

### Guidance

Examples:

- `foodex2-overview.md`
- `base-term-selection.md`
- `implicit-vs-explicit-facets.md`
- `process-facets.md`
- `ingredient-facets.md`

Use for:

- FoodEx2 concepts
- operational coding guidance
- worked examples
- term and facet interpretation

### Validation

Examples:

- `business-rules.md`
- `validation-rules.md`
- `structural-validation.md`
- `term-type-facet-constraints.md`
- `process-validation-rules.md`

Use for:

- validator behavior
- `BRxx` constraints
- syntax and cardinality rules
- raw-vs-derivative and facet legality checks

### Domain Overlay

Examples:

- `chemical-monitoring-foodex2.md`
- `pesticides-foodex2.md`
- `contaminants-foodex2.md`
- `domoic-acid-scallops.md`
- `vmpr-foodex2.md`
- `additives-flavourings-foodex2.md`
- `domain-specific-validation.md`

Use for:

- conditional reporting overlays
- pesticide residue, contaminants, VMPR/VETDRUG, additives, and flavourings domains
- legislative matrix or class mapping
- domain-mandated explicit facets
- substance-specific contaminant rules and infant/baby reporting edge cases

### Maintenance

Examples:

- `maintenance-history.md`
- `maintenance-2015.md`
- `maintenance-2024.md`
- `log.md`

Use for:

- annual changes
- maintenance deltas
- ingest history
- known updates and drift points

## Frontmatter

Every markdown page that is part of the served wiki should use YAML frontmatter.

Preferred fields:

- `title`
- `last_updated`
- `sources`
- `related`

Optional fields:

- `source_inspiration`
- other page-specific metadata when clearly useful

Field meanings:

- `title`: human-readable page title
- `last_updated`: ISO date string
- `sources`: canonical backing sources for the page
- `related`: nearest neighboring wiki pages

## Section Conventions

Not every page needs every section, but pages should follow recognizable patterns.

Recommended sections by page type:

- Guidance pages:
  - concise concept sections
  - worked examples when useful
  - `Relevant Policy`
  - `Relevant Business Rules`
- Validation pages:
  - rule summaries
  - severity or applicability notes
  - worked examples when useful
  - `Relevant Policy`
  - `Relevant Business Rules`
- Runtime pages:
  - purpose
  - execution order or always-on rules
  - references back to richer guidance pages
- Maintenance pages:
  - what changed
  - why it matters
  - links to affected guidance or validation pages

## Linking Rules

- Prefer inline links when one page directly depends on another concept.
- Use `related` in frontmatter for near neighbors.
- Add `Relevant Business Rules` only for `BRxx` rules that materially constrain the page.
- Add `Relevant Policy` when runtime decision order matters for the page.
- Avoid backlink spam. The purpose is navigation, not exhaustiveness.

## Relationship Model

The wiki has a lightweight markdown-native relationship model.

It is graph-like, but it is not a separate graph database or a formal graph engine.

The current architecture intentionally keeps this graph markdown-authored. For the repo's current scale and rare-update pattern, improve links, summaries, graph traversal, and tests before adding an external graph store.

Today the main edge types are:

- `related` in frontmatter: explicit near-neighbor edges between pages.
- Inline `[[page]]` links in the body: conceptual dependency edges used inside explanations, examples, and rule references.
- `Relevant Policy`: control-layer edges from an operational page to `policy-contract.md`.
- `Relevant Business Rules`: validator-layer edges from an operational page to `business-rules.md` and specific `BRxx` constraints.
- `index.md`: catalog and hub node that helps selectors and humans discover the first hop into the graph.

What this means in practice:

- The relationship model is authored in markdown, not in service code.
- The API reads and exposes the `related` frontmatter field directly.
- The selector also benefits from the inline links and section conventions because they make neighboring concepts legible inside retrieved page text.
- Generated graph views can be built from the same markdown without introducing a separate authoring format.
- Backlinks, adjacency maps, or graph traversal can be added later without changing how pages are authored.

See [[KNOWLEDGE_ARCHITECTURE]] for the runtime stance: compiled wiki pages are the durable knowledge layer; long-source indexes are ingest aids; graph expansion should be derived from markdown unless selector evidence proves that heavier infrastructure is needed.

## Runtime Serving Rules

- `RUNTIME_RULES.md` is the compact always-on prompt-facing page for `context-pack`.
- `policy-contract.md` remains the richer control page used by structured and solver-oriented flows.
- `business-rules.md` is not automatically attached to every request. It should be reached through relevant pages and explicit need.

## Ingest Checklist

When adding or revising pages:

1. keep raw sources unchanged
2. update or create the right page type
3. set or refresh frontmatter
4. add inline cross-links
5. add `Relevant Business Rules` where material
6. add `Relevant Policy` where decision order matters
7. update `index.md`
8. run `python -m wiki_api.doctor`
9. update `log.md` if the change is material
