---
title: "Selection Skeleton Policy"
last_updated: "2026-07-05"
source_tier: "local_policy"
sources:
  - "docs/superpowers/specs/2026-07-05-selection-skeleton-design.md"
related:
  - "[[RUNTIME_RULES]]"
  - "[[base-term-selection]]"
  - "[[facet-coding-rules]]"
  - "[[term-type-facet-constraints]]"
---

# Selection Skeleton Policy

This page defines the deterministic failsafe applied to `/wiki/context-pack`
after the LLM page selector runs. It is maintainer policy, not FoodEx2
coding guidance, and is never projected into coding prompts.

## Why This Exists

Every context-pack case constructs a FoodEx2 code, and constructing a code
always requires base-term guidance, facet guidance, and validation guidance.
That is a structural invariant, not a judgment call. The 2026-07-05 baseline
(`reports/selection-evals/2026-07-05-baseline/`) showed the LLM selector
omitting the validation layer in 10 of 15 packs and leaking maintenance
pages into one.

The service backfills a default page for any uncovered role and drops pages
that never belong in a coding pack. Every backfill is logged as a
`selector_miss` and surfaced in the response trace: the failsafe is also a
scoreboard. Improving the selector (Phase 2) should drive the backfill rate
toward zero.

## Bright Line

The deterministic layer may encode general structural invariants only.
It must never encode case-specific content. "All code-construction packs
carry the three roles" is allowed. "When the query says scallop, add the
domoic-acid page" is forbidden — that is selector judgment, forever.
Domain overlays are deliberately not a required role for the same reason.

## Policy Block

The service parses the following block. The doctor validates that every
member and default is a served prompt-facing page and that non-glob drop
entries exist.

```yaml
skeleton_version: 1
required_roles:
  base_term:
    members:
      - base-term-selection.md
    default: base-term-selection.md
  facet:
    members:
      - facet-coding-rules.md
      - implicit-vs-explicit-facets.md
      - process-facets.md
      - ingredient-facets.md
      - packaging-facets.md
      - code-string-format.md
    default: facet-coding-rules.md
  validation:
    members:
      - term-type-facet-constraints.md
      - validation-rules.md
      - structural-validation.md
      - business-rules.md
      - process-validation-rules.md
    default: term-type-facet-constraints.md
drop_pages:
  - "maintenance-*"
  - "README.md"
  - "PROJECT_CONTEXT.md"
  - "KNOWLEDGE_ARCHITECTURE.md"
  - "WIKI_ARCHITECTURE_FOR_MODELS.md"
  - "INGEST_WORKFLOW.md"
  - "MAINTENANCE_WORKFLOW.md"
  - "SCHEMA.md"
  - "log.md"
  - "selection-policy.md"
```
