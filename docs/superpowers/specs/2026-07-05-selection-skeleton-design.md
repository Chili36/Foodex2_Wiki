# Selection Skeleton Failsafe — Design

**Date:** 2026-07-05
**Phase:** 1 of the page-selection improvement plan ([plan](../plans/2026-07-05-page-selection-improvement.md), [issue #32](https://github.com/Chili36/Foodex2_Wiki/issues/32))
**Baseline driving this:** `reports/selection-evals/2026-07-05-baseline/` — mean must-have recall 0.73; `term-type-facet-constraints.md` missing from 10/15 packs; SEL-0014 dropped `base-term-selection.md`; SEL-0009 leaked two maintenance pages.

## Philosophy (agreed with David, 2026-07-05)

The LLM page selector stays the protagonist. This design adds a **measured failsafe**, not a lookup service:

- The deterministic layer may encode **general structural invariants only** — facts true for every code-construction pack regardless of query. It must never encode case-specific content ("query mentions scallop → add domoic page" is forbidden, forever; that is selector judgment).
- Every deterministic intervention is **logged as a selector miss** and surfaced as a **backfill rate** metric. Phase 2's job is to drive that rate toward zero. If it reaches zero, the failsafe never fires and could be deleted.
- The selector prompt is **not changed** in Phase 1 (isolate the variable; also avoid teaching the selector to slack because "the service will fix it").

The invariant being enforced: *every `/wiki/context-pack` response supports constructing a FoodEx2 code, which requires base-term guidance, facet guidance, and validation guidance; and never contains maintenance or orientation pages.*

## Components

### 1. Policy page: `raw/efsa-guidance/selection-policy.md`

A served wiki page, category **`orientation`** (served and doctor-checked, but never prompt-projected; if the selector ever picks it, the drop rule removes it — self-healing). Registered in the `WikiStore` category map and `index.md`.

Content: prose explaining the failsafe philosophy and the bright line (structural invariants only), followed by one fenced ` ```yaml ` block the service parses:

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
  - "maintenance-history.md"
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

Notes:
- Domain overlays are deliberately **not** a required role: conditional, query-dependent, selector's judgment (Phase 2).
- `policy-contract.md` and `RUNTIME_RULES.md` are untouched by roles (RUNTIME_RULES is already always front) and are not droppable.
- Role members define *coverage* (any member satisfies the role); the default is what gets backfilled when no member is present.

### 2. Enforcement module: `wiki_api/selection_policy.py`

Pure functions, no I/O beyond reading the policy page via `WikiStore`:

- `load_selection_policy(store) -> SelectionPolicy` — extracts and parses the YAML block from `selection-policy.md`; raises with a clear message on missing page/block/invalid schema. Cached at module/app level, invalidated with store reload (match existing store caching idiom).
- `enforce_skeleton(pages_used: list[str], policy: SelectionPolicy) -> SkeletonResult` — for each required role in declaration order: if no member present in `pages_used`, append the role default (after selected pages; `RUNTIME_RULES.md` front-position untouched). Remove any page matching `drop_pages` (fnmatch). Never reorders or deduplicates beyond that.
- `SkeletonResult`: `final_pages: list[str]`, `backfilled: list[{role, page}]`, `dropped: list[str]`, `selector_covered_roles: list[str]`.

Backfill **ignores `max_pages`** — correctness for the downstream coder beats the page budget; overruns are visible in the trace and in eval pack-size numbers (token budgeting is Phase 4's problem).

### 3. Integration: `create_context_pack` in `wiki_api/app.py`

Between selection and response assembly: run `enforce_skeleton` on `selection_result.pages_used`, build `pages` from `final_pages`. Add to response `trace`:

```json
"skeleton_enforcement": {
  "policy_version": 1,
  "backfilled": [{"role": "validation", "page": "term-type-facet-constraints.md"}],
  "dropped": ["maintenance-2019.md"],
  "selector_covered_roles": ["base_term", "facet"]
}
```

Each backfill also emits a `logger.info("selector_miss ...")` line with role, page, and search_term. `/wiki/ask` and `/wiki/policy-pack` are **out of scope** (context-pack is the DMT surface; extending later is trivial once proven).

### 4. Doctor check: `wiki_api/doctor.py`

New deterministic checks: `selection-policy.md` exists, is registered, parses; every role member and default exists as a served prompt-facing page; every `drop_pages` literal (non-glob) exists as a served page; role defaults are members of their own role. A broken policy page fails the doctor loudly.

### 5. Eval runner: backfill-rate metric

`scripts/selection_eval.py` reads `trace.skeleton_enforcement` per case and reports per-case `backfilled`/`dropped` plus a summary `backfill_rate` (mean backfills per case and fraction of cases with ≥1 backfill). Recall/precision/leak scoring is unchanged — the scorer sees post-enforcement `pages_used`, which is what the downstream consumer receives.

## Testing

- Unit (`tests/test_selection_policy.py`): role covered → no backfill; role missing → default appended in role order; drop-list literal + glob removal; combined backfill+drop; empty selection → all three defaults; malformed/missing YAML → clear error; result ordering stable.
- Integration (`tests/test_wiki_api.py` pattern, stubbed selector): context-pack response contains backfilled pages, trace block present, dropped page absent, RUNTIME_RULES still front.
- Doctor test: corrupted policy block → doctor failure entry.
- End-to-end: rerun `scripts/selection_eval.py --label phase1 --only-reviewed` against the live API; compare with baseline.

## Acceptance (from the plan's Phase 1 gate)

- Gold-set leak-free rate → 1.0; validation-page recall gap closed (projected mean recall ≥ ~0.90 from 0.73).
- No precision collapse (defaults are on-topic; expected to land in must_have/acceptable).
- Selector token cost unchanged (selector call untouched).
- Backfill rate reported and non-zero (the scoreboard exists and is honest).
- Residual judgment misses (SEL-0005 process-validation, SEL-0011 implicit-vs-explicit) remain — they are Phase 2's evidence, not Phase 1 failures.

## Out of scope

Selector prompt changes, candidate-awareness, index summary rewrites (Phase 2); token budgets (Phase 4); `/wiki/ask` + `/wiki/policy-pack` enforcement; moving the page-category map out of `wiki_store.py` (noted as future cleanup — categories are service-side today; the *policy* over categories now lives in markdown).
