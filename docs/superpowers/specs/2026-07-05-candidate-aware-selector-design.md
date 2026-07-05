# Candidate-Aware Selector + Selection Metadata — Design

**Date:** 2026-07-05
**Phase:** 2 of the page-selection improvement plan ([plan](../plans/2026-07-05-page-selection-improvement.md), [issue #33](https://github.com/Chili36/Foodex2_Wiki/issues/33))
**Prior art:** Phase 1 shipped the skeleton failsafe (spec: [2026-07-05-selection-skeleton-design.md](2026-07-05-selection-skeleton-design.md)); its `backfill_case_rate` of **0.9333** is the number this phase exists to drive down.

## Philosophy (agreed with David, 2026-07-05)

Phase 1 made packs *complete* deterministically; Phase 2 makes the **LLM selector smarter** so the deterministic layer stops firing. Nothing in this phase adds deterministic selection: the selector is taught *meaning* (what termTypes imply, what situations pages serve) and then judges. The Phase 1 failsafe stays untouched as the safety net that makes selector experiments risk-free for downstream consumers.

**Bright line, extended to metadata phrasing:** selection hints describe *situations and concepts a page helps with* — never query-string → page mappings ("select when the query mentions scallops" is forbidden), never termType → filename rules. The LLM lint checks for this phrasing.

**Terminology:** "selector catalog" = generated metadata about *our wiki pages*. EFSA's FoodEx2 term catalogue is untouched and unowned by us, as always.

## Decisions made in brainstorming

1. **Candidate-awareness mechanism: teach the selector.** No service-computed candidate digest (evidence-gated fallback only if a future eval shows weak models failing to parse raw candidate hints).
2. **Metadata shape: a single `select_when` prose frontmatter field.** No `signals` keyword list, no structured condition objects.
3. **Acceptance bar:** median of 3 eval runs — `backfill_case_rate` ≤ 0.33, SEL-0005 + SEL-0011 closed by the selector itself, recall/precision/leak-free no worse than phase1, selector token cost ≤ +50% vs phase1 (~5,400 tokens/case ceiling).
4. **Annotation scope: all ~25 prompt-facing pages**, LLM-written. Per-page effort is not a constraint (LLM-driven maintenance is the operating model); QA machinery is.

## Components

### 1. `select_when` frontmatter on prompt-facing pages

Every page in categories `runtime`, `guidance`, `validation`, `domain_overlay` gains:

```yaml
select_when: >-
  The case involves deciding whether descriptive detail (process, source,
  physical state) is already implicit in a candidate base term or must be
  added as an explicit facet — especially when candidates include
  derivative terms.
```

Writing rules (go in `SCHEMA.md`):
- Situation/concept vocabulary; complete sentences; ≤ ~60 words.
- Forbidden: query keywords ("when the query says…"), filename references, termType→page mappings, marketing language.
- Orientation and maintenance pages do NOT get the field (they are never selector-eligible; the Phase 1 drop rule removes them anyway).

### 2. Generated selector catalog (replaces `index.md` as selector input)

`WikiStore` gains `selector_catalog() -> str`: for each prompt-facing page, one entry `page-name.md — <select_when>`, falling back to the page's `index.md` summary line when `select_when` is absent (**graceful degradation** — an unannotated page is disadvantaged, never invisible). Assembled at request time like summaries today; no build step, no generated file. `index.md` itself is unchanged and stays human-facing.

Both selector classes (`AnthropicWikiPageSelector`, `JsonWikiPageSelector` in `wiki_api/librarian.py`) send the catalog in place of `wiki_index`. Note: the selector runner is shared with `/wiki/ask`, so ask benefits incidentally; enforcement and eval remain context-pack-scoped.

### 3. Selector Guidance in `selection-policy.md`

`selection-policy.md` gains a **`## Selector Guidance`** prose section, service-loaded and injected into the selector system prompt (the hardcoded prompt in `librarian.py` shrinks to scaffolding: task statement, JSON format, page limit). Content:

- **Reading candidates:** what termTypes mean (`r` raw, `d` derivative, `c`/`s` composite, `h`/`g` hierarchy/group, `f` facet, `n` non-specific — consistent with `term-type-facet-constraints.md`); that group/facet terms in a candidate set mean the coder must be steered away from them; that mixed raw+derivative candidate sets signal implicit-vs-explicit decisions ahead.
- **Reading context:** explicit `reporting_domain` activates overlay thinking; absence of domain signals means all-domain default.
- **Completeness rubric:** a code will be constructed from this pack — it must let the coder resolve food type, base-term choice, facet legality, and validation; think about what THIS case makes hard, and pick pages whose `select_when` matches those difficulties.
- Explicitly restates the bright line: reason from meanings, not keyword matches.

Loading: same fenced-block-free prose extraction pattern — service reads the section body from the page (a `load_selector_guidance(store)` function beside `load_selection_policy`). Doctor errors if the section is missing or empty. Per-request re-read, matching the established no-caching idiom.

### 4. QA machinery for LLM-written metadata

- **Doctor (deterministic):** every prompt-facing page has non-empty `select_when` ≤ 400 chars; `Selector Guidance` section present in `selection-policy.md`. New check name `selection_metadata`, same `DoctorIssue` pattern.
- **LLM lint (supervised):** new lint focus prompt for `select_when` hygiene — situation-phrasing (bright line), accuracy vs page content, no overlap-blur between sibling pages. Run via existing `python -m wiki_api.llm_lint --page <page> --focus ...`; not a CI gate, a maintainer aid, per existing lint posture.
- **Eval (empirical):** the gold set is the final judge; bad hints show up as unmoved backfill rate.

### 5. Ingest/schema documentation

- `SCHEMA.md`: field definition, writing rules, examples (one good, one bright-line-violating).
- `INGEST_WORKFLOW.md`: new step — every created or materially patched prompt-facing page gets `select_when` written/refreshed; doctor enforces existence.

### 6. Eval protocol (variance first)

- **Task 0:** `scripts/selection_eval.py` gains `--repeats N` (default 1): run each case N times, report per-metric median and min/max in the summary, per-run detail in results.json. Re-run **phase1 configuration with `--repeats 3`** to establish the honest pre-change reference (`reports/selection-evals/<date>-phase1-r3/`).
- **After implementation:** `--repeats 3` phase2 run; compare medians.
- **Iteration cap (anti-oscillation, per David's prompt-iteration-limits rule):** if the acceptance bar is missed, at most **two** revision rounds of guidance/metadata wording; still short → stop, write findings, reassess structurally (that becomes Phase 3 evidence).

## Acceptance criteria

Median of 3 runs on the 15-case gold set, all relative to the phase1-r3 reference:

1. `backfill_case_rate` ≤ 0.33 (reference ~0.93).
2. SEL-0005 (`process-validation-rules.md`) and SEL-0011 (`implicit-vs-explicit-facets.md`) selected by the selector itself (not backfilled) in ≥ 2 of 3 runs.
3. `mean_must_have_recall`, `mean_precision`, `leak_free_rate` each ≥ phase1-r3 medians (the failsafe guarantees the floor; this checks the selector isn't churning).
4. Selector `total_tracked_tokens`/case median ≤ 1.5 × phase1-r3 median (≈ ≤ 5,400).
5. Doctor clean (including new checks); full test suite green; lint pass run over all annotated pages with findings triaged.

## Out of scope

Phase 1 failsafe changes; Qdrant/lexical recall shortlist (Phase 3, evidence-gated); candidate digest preprocessing (evidence-gated); `/wiki/solve` and `/wiki/policy-pack` prompts; `/wiki/ask` answerer; any LLM model name changes; `evals/selection/gold_cases.json` label changes (the ground truth does not move while we tune the thing it measures).

## Addendum (post-review fix, 2026-07-05)

Two review findings landed after the initial phase 2 merge and were fixed together (branch `feature/phase2-candidate-aware-selector`, commit after `359063a`):

**Finding P2 (regression):** `selector_catalog()` originally had one shape — prompt-facing pages only (`PROMPT_CONTEXT_PAGE_CATEGORIES`) — reused by both `/wiki/context-pack` and `/wiki/ask` (per the note in Component 2 above: "the selector runner is shared with `/wiki/ask`, so ask benefits incidentally"). That single shape was correct for context-pack (its skeleton enforcement drops non-prompt-facing pages anyway) but was a regression for `/wiki/ask`: before this phase, both selector classes saw the full `index.md`, so `/wiki/ask` could discover orientation/maintenance/log pages (e.g. answering "what changed in the 2024 maintenance release?" with `maintenance-2024.md`). Restricting the catalog to prompt-facing categories made those pages unselectable for `/wiki/ask` too, even though nothing about `/wiki/ask`'s job requires that restriction.

**Finding P3 (slot waste):** `/wiki/context-pack` unconditionally front-injects `RUNTIME_RULES.md` (`_ensure_front_page`), so the selector spending one of its limited picks selecting it (redundantly) was pure waste in the coding-scope catalog. For `/wiki/ask` there is no such front-injection, so `RUNTIME_RULES.md` is a legitimately selectable page there.

**Fix: two catalog scopes.** `WikiStore.selector_catalog(scope: str = "coding")` now branches:

- `scope="coding"` — prompt-facing pages (`PROMPT_CONTEXT_PAGE_CATEGORIES`) **excluding `RUNTIME_RULES.md`**. Used by `/wiki/context-pack`.
- `scope="ask"` — every served page except `index.md`: prompt-facing pages (including `RUNTIME_RULES.md`) plus orientation, maintenance, and `log.md`. Used by `/wiki/ask`. Non-prompt-facing pages have no `select_when` hint, so they fall back to their `index.md` summary (or title) — the same graceful-degradation rule as before, just no longer gated to prompt-facing categories for this scope.
- Any other value raises `ValueError`.

`build_selection_user_content(*, store, payload, scope="coding")` threads the scope through, and both selector classes (`AnthropicWikiPageSelector`, `JsonWikiPageSelector`) take a `catalog_scope: str = "coding"` constructor parameter used when building the user message. The `run(payload)` signature is unchanged.

**Wiring (`app.py`):** `get_selector_runner` gained a `scope` parameter. Two separate module-level singletons — `selector_runner` (coding) and `ask_selector_runner` (ask) — are each constructed once with their `catalog_scope` fixed at construction time and never mutated afterwards; per-request model/effort overrides likewise bake `catalog_scope` in at construction. This avoids the file's existing shared-runner-mutation footgun (`max_pages` is already mutated in place on the cached singleton) — scope is never mutated post-construction on a shared instance, so `/wiki/context-pack` and `/wiki/ask` cannot cross-contaminate each other's catalog even when both hit the no-override code path in the same running process.

**Verification:** `/wiki/ask` re-tested live against "What changed for FoodEx2 in the 2024 maintenance release?" — the selector itself (not graph expansion) picked `maintenance-2024.md`, confirming the regression is fixed. The phase2 eval was re-run against `/wiki/context-pack` (`phase2-r3-askfix`, `--repeats 3`) to confirm removing `RUNTIME_RULES.md` from the coding catalog was neutral-or-better: all five acceptance criteria still pass, with every metric equal to or better than the `phase2-r3` (rev2) reference (see `reports/selection-evals/2026-07-05-phase2-r3-askfix/triage.md`).
