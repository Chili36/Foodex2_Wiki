# Expand & Re-measure Selection Eval — Design

**Date:** 2026-07-05
**Phase:** 3 of the page-selection improvement plan ([plan](../plans/2026-07-05-page-selection-improvement.md))
**Prior art:** Phases 0-2 shipped to main (PRs #36, #37). Phase 2 left `/wiki/context-pack` must-have recall at a median 0.967.

## The finding that reframes Phase 3

The Phase 2 request was "raise recall past the validation-role gap." Investigation of the committed eval data shows the recall ceiling is **not a stable structural gap** — it is measurement noise on a too-small, too-uniform gold set:

- Accepted phase2-r3 run: recall 0.967, but a *different* case misses on every pass (pass0 SEL-0005+SEL-0008, pass1 SEL-0001+SEL-0013, pass2 SEL-0011). No case fails consistently.
- The phase2-r3-askfix run (identical code): recall **1.000**, zero misses across all three passes.

The swing between two runs of the same code (±0.033 ≈ one case on 15 cases) is as large as any improvement a recall mechanism could plausibly produce. **You cannot measure a recall fix on this eval today.**

The deeper cause is coverage, not statistics. Current must-have frequency across the 15 cases:

| Page | must-have in N cases |
| --- | --- |
| base-term-selection.md | 15 |
| term-type-facet-constraints.md | 14 |
| vmpr-foodex2.md | 5 |
| facet-coding-rules.md | 4 |
| pesticides / contaminants / additives overlays | 3 each |
| ingredient-facets.md | 3 |
| process-facets / process-validation-rules / implicit-vs-explicit / packaging-facets | 1 each |
| **structural-validation.md / validation-rules.md / business-rules.md / code-string-format.md** | **0 each** |

The within-role gap ("role covered, but by the wrong specific page") is *invisible* because almost every case's validation must-have is the default page (`term-type-facet-constraints`) that the failsafe backfills anyway, and four prompt-facing pages are never a must-have in any case. The instrument literally cannot see the defect it was asked to fix.

## Philosophy (agreed with David, 2026-07-05)

Do not build a recall mechanism against an eval that cannot measure it — that is overfitting to noise, which the project's standing rules forbid. Phase 3 rebuilds the measuring instrument, re-measures honestly, and **gates any mechanism on whether a real ceiling survives**. Not every phase ends in a build; "the ceiling was noise" is a valid, valuable outcome. This phase changes only the eval assets (`evals/`, `scripts/selection_eval.py`, `reports/`) — no wiki pages, no selector, no failsafe.

## Decisions made in brainstorming

1. **Scope:** expand + re-measure first; build a recall mechanism only if the expanded, higher-repeat eval reveals a *systematic* ceiling.
2. **Case sourcing:** mine real cases from the DMT corpus, plus targeted synthetic cases for under-covered pages.
3. **Label review:** LLM cross-check labels every new case independently; only cross-check *disagreements* are surfaced for David's review (effort scales with ambiguity, not case count).

## Components

### 1. Coverage-targeted gold-set expansion (15 → ~38 cases)

**Coverage floor (the acceptance target for the expansion itself):** every prompt-facing validation page (`term-type-facet-constraints`, `validation-rules`, `structural-validation`, `business-rules`, `process-validation-rules`) and every facet page (`facet-coding-rules`, `implicit-vs-explicit-facets`, `process-facets`, `ingredient-facets`, `packaging-facets`, `code-string-format`) is a must-have in **≥ 3 cases**. This is what makes per-page within-role selection measurable.

**Sourcing:**
- *Real:* mine `foodex2_eval_cases_from_facet_review.json` (37 labelled cases: `query`, `must_base`, facets) and `foodex2_advisory_cache.json` (food descriptions) from `/Users/davidfoster/dev/guidance_with_claude/data/` (read-only; that repo is not modified). Convert each into a context-pack request (search_term = query, candidate_hints from `must_base`/facets where available, domain from context).
- *Synthetic:* fill remaining coverage-floor gaps — cases that genuinely require `structural-validation` (syntax/descriptor-existence/cardinality problems), `business-rules` (a specific BR at stake), `validation-rules` (multi-layer/severity questions), `code-string-format` (code-string assembly focus), `packaging-facets`, `process-facets`. Label from the pages' actual content, per the existing rubric.

New case IDs continue the `SEL-00NN` sequence; `source` records origin (`dmt:<file>:<id>` or `synthetic`). All new cases start `reviewed: false`.

### 2. LLM cross-check labeling (`scripts/gold_crosscheck.py`, new)

A second model independently produces three-tier labels for each new case from the same rubric + page catalog, without seeing the drafter's labels. The script diffs cross-check vs draft per case and writes `reports/gold-crosscheck/<date>/report.md`: agreements (auto-accept), and disagreements (must_have/must_not deltas) flagged for David. David reviews only the disagreement list, resolves each, then the case flips `reviewed: true`. Agreements are trusted (two independent models from the same rubric concurring is the bar). This is a maintainer aid, not a CI gate.

### 3. Per-case stability metric in the runner (`scripts/selection_eval.py`)

Add, alongside the existing median summary: a **miss-frequency table** — for each (case_id, missing_page), the count of passes (out of `--repeats`) that dropped it. Summary gains `systematic_misses` (page missed in ≥ ceil(2/3 · repeats) passes of a case) and `stochastic_misses` (missed in fewer). This is the instrument that separates the two failure modes the whole phase turns on. No scoring-semantics change; `score_case`/`aggregate` untouched.

### 4. phase3-baseline run (repeats = 5)

Run the current post-Phase-2 selector against the expanded, reviewed gold set at `--repeats 5`, committed to `reports/selection-evals/<date>-phase3-baseline/`. Odd repeat count for a clean median; 5 to damp per-case selector dice. This is the new honest reference.

### 5. Decision gate + triage (the deliverable)

`reports/selection-evals/<date>-phase3-baseline/triage.md` answers one question with data: **is there a systematic within-role ceiling?**
- **Yes** (specific non-default pages appear in `systematic_misses` across multiple cases): document exactly which pages/situations the selector systematically fails to pick — that is the measurable target. Recommend a follow-up phase (completeness-critic or targeted guidance) to be built and proven against this now-sensitive set. Do NOT build it in this phase.
- **No** (misses remain stochastic even with coverage + 5 repeats): state plainly that recall is effectively solved and the earlier "ceiling" was noise. Phase 3 ends with a truthful negative result and no mechanism.

## Acceptance criteria

1. Gold set ≥ 35 cases; coverage floor met (every listed validation and facet page must-have in ≥ 3 cases); mechanical validation passes (all labeled non-glob pages exist; no must_have/acceptable ↔ must_not overlap; every case `reviewed: true`).
2. Cross-check run committed; all disagreements resolved by David; agreements auto-accepted.
3. Runner emits the per-case miss-frequency table and `systematic_misses`/`stochastic_misses`; existing metrics unchanged; full suite green.
4. phase3-baseline (repeats = 5) committed with `triage.md` giving a data-backed yes/no on the systematic ceiling and a gated recommendation.
5. No changes to wiki pages, selector, or failsafe; no LLM model names changed; the DMT repo is read-only.

## Out of scope

Any recall mechanism (critic pass, targeted guidance, retrieval backstop) — explicitly gated behind Phase 3's finding; `/wiki/ask` eval (separate running task `task_f9d0630f`); token budgeting (master-plan Phase 4); `evals/selection/gold_cases.json` label changes to the original 15 (they stay; only additions); any selector prompt or `select_when` edits.
