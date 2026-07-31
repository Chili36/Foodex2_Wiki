---
title: "Selection Skeleton Policy"
last_updated: "2026-07-29"
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
after the LLM page selector runs, and carries the selector guidance injected
into the page selector's system prompt. It is maintainer policy, not FoodEx2
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
  - "index.md"
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

## Selector Guidance

This section is loaded by the wiki service and injected into the page
selector's system prompt. It teaches the selector how to read a coding
case. It describes meanings and situations only — it must never map query
keywords or term types to page filenames.

### Reading The Candidate List

- Candidate `termType` values follow the FoodEx2 term-type model:
  `r` raw commodity, `d` derivative, `c` composite, `s` simple composite,
  `h` hierarchy, `g` generic or group, `f` facet descriptor, and
  `n` non-specific.
- A candidate set that mixes raw and derivative terms for the same
  commodity means the coder must decide which descriptive details are
  already implicit in a derivative base and which need explicit facets.
  Prefer pages whose selection hints cover implicit-versus-explicit
  reasoning and raw-versus-derivative process boundaries.
- Hierarchy, group, facet, or non-specific terms in the candidate list are
  traps: they are discouraged or invalid as reportable base terms, and the
  coder must be steered toward a legal specific term. When such candidates
  appear, prefer pages whose hints cover base-term legality and term-type
  constraints.

### Reading The Context

- An explicit reporting domain in the case context activates exactly that
  domain's overlay thinking. Never select overlay pages for domains the
  case does not signal; with no domain signal, the all-domain default
  applies and no overlay page belongs in the pack.
- One overlay is usually enough. Prefer the page specific to the signalled
  domain over umbrella monitoring overlays, and do not spend pack slots on
  both unless the case genuinely spans several domains.
- Processing, packaging, ingredient, mixture, or physical-state details in
  the query or deconstructed query are real coding work. Prefer pages
  whose hints cover those facet families and the validation rules that
  constrain them.

### Completeness Rubric

A FoodEx2 code will be constructed from the pack you assemble. The pack
must let the coder resolve the food type, the best reportable base term,
which facets are legal and needed, and how the construction will be
validated. The pack must serve the code the coder will produce: a
construction that will carry explicit facet segments needs assembly-syntax
and dataset-review coverage, not only concept pages. Ask what this
specific case makes difficult, then choose the
pages whose selection hints address those difficulties. Do not pad the
pack with pages the case does not need.

Every constructed code faces validation, even when the query never
mentions it. A pack that says nothing about how the construction will be
checked is incomplete: include the pages whose hints cover validating the
code you expect the coder to build. These needs are cumulative, not
alternatives — a food that has been treated or preserved needs
process-rule coverage, and facets attached to the chosen base term need
facet-legality coverage. Domain-specific validation overlays supplement
this core coverage; they never replace it.
