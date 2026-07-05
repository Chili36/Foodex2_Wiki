# Phase 1 Triage — 2026-07-05

Phase 1 run: `scripts/selection_eval.py --label phase1 --only-reviewed` against a fresh
`uvicorn wiki_api.app:app` instance on port 8011 (the long-running instance on 8010 predated
the skeleton-enforcement merge and was left untouched — see "API instance" note below), 15
reviewed cases, same gold set as baseline.

## Baseline vs Phase 1

| Metric | Baseline | Phase 1 | Δ |
| --- | --- | --- | --- |
| Mean must-have recall | 0.7278 | 0.9667 | +0.239 |
| Mean precision | 0.9144 | 0.9600 | +0.046 |
| Leak-free rate | 0.9333 (1 case leaked) | 1.0000 (0 leaked) | +0.067 |
| Mean pack chars | 16,031 | 18,791 | +2,760 (+17%) |
| Backfill case rate | n/a (metric new) | 0.9333 (14/15 cases) | — |
| Mean backfills per case | n/a (metric new) | 1.067 | — |

Selector token cost is unchanged: mean total tracked tokens per case 3593 (baseline) vs 3644
(phase1), a ~1.4% difference well within call-to-call noise — the skeleton enforcement runs
*after* the selector call and adds no LLM cost.

## Misses closed

- **`term-type-facet-constraints.md`** (10/15 cases in baseline: SEL-0001, 2, 3, 4, 6, 7, 8,
  9, 10, 14) — closed in all 10 by backfill. This was the dominant, whole-category miss
  identified in the baseline triage; the deterministic validation-role floor fixes it in every
  case it applies to.
- **`base-term-selection.md`** (SEL-0014) — closed. The selector picked it up on this run
  without needing a backfill (`backfilled` is empty for SEL-0014 aside from the validation
  page), so recall 1.0/precision 1.0 for this case; worth flagging as run-to-run variance (see
  Caveat) rather than attributing solely to the skeleton, though the skeleton would have
  backfilled `base_term` role if the selector had dropped it again.
- **`facet-coding-rules.md`** (SEL-0010, SEL-0012) — closed in both by backfill.
- **Maintenance-page leak** (SEL-0009: `maintenance-2019.md`, `maintenance-2022.md`) — closed.
  In this run the selector itself did not select the maintenance pages (the `dropped` list for
  SEL-0009 is empty), so leak-free rate reaching 1.0 here reflects selector-side variance for
  this specific case, not the drop-rule triggering. The drop rule exists in the enforcement
  path (Task 2/3) and would remove maintenance/orientation pages if the selector picked them
  again; this run didn't exercise that code path for SEL-0009. Flagged as a residual
  verification gap, not a regression.

## Misses remaining

- **SEL-0005** (`process-validation-rules.md`, recall 0.75) — remains, as predicted. This is
  the process-validation page for a processed/additives case; the category skeleton backfills
  the generic `validation` role (`term-type-facet-constraints.md`) but does not know to prefer
  the *process*-specific validation page over the general one. Phase 2 candidate-signal
  evidence.
- **SEL-0011** (`implicit-vs-explicit-facets.md`, recall 0.75) — remains, as predicted. The
  skeleton backfilled `facet-coding-rules.md` (facet role) but the case needs the
  derivative/`termType: d`-specific facet page, which is a candidate-aware pick, not a
  category-level one. Phase 2 candidate-signal evidence.
- No surprises: both residuals are exactly the two the baseline triage flagged as Phase 2
  candidates (candidate-aware selector, not category skeleton), and no new misses or leaks
  appeared elsewhere in the 15-case set.

## Acceptance criteria assessment

Per the spec's Phase 1 acceptance criteria: leak-free rate is 1.0 (met, up from 0.933);
mean must-have recall is 0.967, comfortably above the ~0.90 target (met, +23.9pp over
baseline); precision moved from 0.914 to 0.960 with no collapse (met — the skeleton backfills
on-topic category pages, so they land as true positives rather than diluting precision);
selector token cost is unchanged at ~3600 tokens/case since enforcement is a post-hoc,
non-LLM step (met); and the new backfill-rate metrics are now reported and wired into the
runner and results.json — 93.3% of cases required at least one backfill (mean 1.07 backfills/
case), confirming the selector alone was under-selecting the validation/facet skeleton before
enforcement, and that the deterministic floor is doing real, load-bearing work rather than
being a no-op safety net. All Phase 1 acceptance criteria are met. The two remaining misses
(SEL-0005, SEL-0011) are exactly the Phase 2 candidate-signal residuals anticipated in the
baseline triage and should not be chased with more Phase 1 tuning — they motivate the
candidate-aware selector work already queued as Phase 2. One caveat carried over from baseline
still applies: this is a single run per case against a non-deterministic LLM selector, so the
SEL-0009 leak-closure and SEL-0014 recall-closure should be treated as point estimates: rerun
2-3x before treating borderline-case results (specifically SEL-0009's drop-path exercise) as
proven rather than lucky.

## API instance note

The long-running process on port 8010 (PID predates this session) was confirmed stale via a
minimal `/wiki/context-pack` POST — its response had no `trace.skeleton_enforcement` key. Per
instructions that instance was left running untouched. A fresh instance was started for this
run only, via the project's `.venv` (`.venv/bin/uvicorn wiki_api.app:app --port 8011`), which
does have the enforcement code live (confirmed via the same minimal-POST check, which returned
`policy_version`, `backfilled`, `dropped`, `selector_covered_roles`). The eval was run with
`--base-url http://127.0.0.1:8011`. The 8011 instance was stopped after the run completed.
