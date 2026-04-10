---
title: "Wiki Schema"
last_updated: "2026-04-10"
sources:
  - "PROJECT_CONTEXT.md"
  - "INGEST_WORKFLOW.md"
  - "README.md"
related:
  - "[[PROJECT_CONTEXT.md]]"
  - "[[INGEST_WORKFLOW.md]]"
  - "[[RUNTIME_RULES.md]]"
  - "[[policy-contract]]"
---

# Wiki Schema

This file defines the page types, frontmatter, and section conventions for the FoodEx2 wiki.

It exists so ingest passes stay consistent and so external callers can understand what kind of page they are looking at.

## Layer Model

The repo has four practical layers:

1. `foodex2_docs/`: immutable source material
2. `raw/efsa-guidance/`: compiled markdown knowledge pages
3. root runtime and maintenance docs such as `RUNTIME_RULES.md`, `README.md`, and this file
4. `wiki_api/`: retrieval and serving layer

Do not write generated interpretations back into `foodex2_docs/`.
Do not move canonical policy or runtime guidance into service code when it can live as markdown.

## Page Types

### Orientation

Examples:

- `README.md`
- `PROJECT_CONTEXT.md`
- `INGEST_WORKFLOW.md`
- `SCHEMA.md`

Use for:

- repo purpose
- architecture
- ingest method
- maintenance conventions

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
- `domain-specific-validation.md`

Use for:

- domain-specific reporting overlays
- VMPR/VETDRUG
- additives
- acrylamide
- infant/baby reporting edge cases

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
8. update `log.md` if the change is material
