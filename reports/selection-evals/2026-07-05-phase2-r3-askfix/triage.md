# Post-Review Fix Triage — 2026-07-05 (phase2-r3-askfix)

Re-run after fixing two review findings on PR #37 (branch `feature/phase2-candidate-aware-selector`):

- **P2 (regression):** `/wiki/ask` lost discoverability of non-prompt-facing pages (e.g.
  `maintenance-2024.md`) because the shared `selector_catalog()` was narrowed to prompt-facing
  categories only — correct for `/wiki/context-pack`, a regression for `/wiki/ask`.
- **P3 (slot waste):** `RUNTIME_RULES.md` stayed selectable in the coding-scope catalog even
  though `/wiki/context-pack` always front-injects it (`_ensure_front_page`), wasting one of the
  selector's limited picks.

Fix: `WikiStore.selector_catalog(scope)` now has two scopes — `"coding"` (prompt-facing minus
`RUNTIME_RULES.md`, used by `/wiki/context-pack`) and `"ask"` (all served pages except
`index.md`, including `RUNTIME_RULES.md`, orientation, maintenance, and `log.md`, used by
`/wiki/ask`). Full design rationale: `docs/superpowers/specs/2026-07-05-candidate-aware-selector-design.md`
("Addendum (post-review fix, 2026-07-05)").

This eval re-run checks that removing `RUNTIME_RULES.md` from the coding-scope catalog did not
regress `/wiki/context-pack` selection quality — same gold set, same protocol as `phase2-r3`
(`scripts/selection_eval.py --only-reviewed --repeats 3`), against a fresh
`.venv/bin/python -m uvicorn wiki_api.app:app --port 8013` instance started for this task
(instance stopped after the run).

## Metric table (medians, with min–max across the 3 passes)

| Metric | phase1-r3 (ref) | phase2-r3 rev2 (prior accepted) | **phase2-r3-askfix** |
| --- | --- | --- | --- |
| Mean must-have recall | 0.9667 (0.95–0.9667) | 0.9667 (0.9611–0.9833) | **1.0000** (1.0–1.0) |
| Mean precision | 0.9733 (0.9733–0.9733) | 0.9889 (0.9867–1.0) | **1.0000** (0.9889–1.0) |
| Leak-free rate | 1.0000 | 1.0000 | **1.0000** |
| Backfill case rate | 0.8667 (0.8667–0.8667) | 0.2000 (0.1333–0.2667) | **0.0000** (0.0–0.1333) |
| Mean backfills/case | 1.0000 | 0.2000 | **0.0000** (0.0–0.1333) |
| Mean selector tokens | 3654.5 (3650.5–3664.6) | 3553.2 (3548.9–3563.5) | **3457.9** (3457.7–3461.9) |
| Mean pack chars | 18,347 | 18,725 | **20,705** (20,273.9–21,115.7) |

Per-pass raw summaries (`reports/selection-evals/2026-07-05-phase2-r3-askfix/results.json`):

| Pass | Recall | Precision | Leak-free | Backfill rate | Tokens |
| --- | --- | --- | --- | --- | --- |
| 1 | 1.0000 | 0.9889 | 1.0000 | 0.0000 | 3457.7 |
| 2 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 3457.9 |
| 3 | 1.0000 | 1.0000 | 1.0000 | 0.1333 | 3461.9 |

Pass 3's single backfill case pair (SEL-0014, SEL-0015) both backfilled `base-term-selection.md`
under the `base_term` role — an isolated miss, not a systemic regression (passes 1 and 2 have
zero backfills).

## Acceptance verdict (askfix medians vs phase1-r3 reference, same bar as phase2-r3)

1. **backfill_case_rate ≤ 0.33** — PASS. 0.0000 median, better than rev2's 0.2000 and far
   better than the 0.8667 reference.
2. **SEL-0005 + SEL-0011 closed by the selector (≥ 2 of 3 passes)** — PASS, improved to 3/3.
   `process-validation-rules.md` (SEL-0005) and `implicit-vs-explicit-facets.md` (SEL-0011) were
   both selector-picked (not backfilled) in all 3 passes; see per-case detail below.
3. **recall / precision / leak-free ≥ reference medians** — PASS. Recall 1.0000 vs 0.9667 (an
   improvement, not just equal — a first for this metric across all recorded runs), precision
   1.0000 vs 0.9733, leak-free 1.0 vs 1.0.
4. **mean_selector_tokens ≤ 1.5 × 3654.5 (≈ 5482)** — PASS. 3457.9, ~5% below rev2 (3553.2) and
   ~5.4% below the phase1-r3 reference. Removing `RUNTIME_RULES.md` from the coding catalog (one
   fewer candidate entry per selector call, and one fewer plausible-but-wasted pick) did not
   increase token cost — if anything the smaller catalog is marginally cheaper to read.
5. **Doctor clean, full suite green** — PASS. `wiki_api.doctor`: 0 errors, 0 warnings; 103/103
   tests pass (up from 88 at phase2-r3 — added catalog-scope, librarian-scope, and
   cross-contamination-guard tests for the P2/P3 fix).

**Conclusion: every criterion passes, and every metric matches or improves on the prior accepted
configuration (rev2). The fix is neutral-or-better for `/wiki/context-pack` as required — no
tuning was needed, so no revision round was consumed.**

## SEL-0005 / SEL-0011 per-pass detail

`pvr` = `process-validation-rules.md` selected by the selector (not backfilled);
`ivef` = `implicit-vs-explicit-facets.md` selected by the selector.

| Run | SEL-0005 pvr | SEL-0011 ivef |
| --- | --- | --- |
| phase1-r3 | 0/3 | 0/3 |
| phase2-r3 (initial) | 0/3 | 3/3 |
| phase2-r3-rev1 | 1/3 | 3/3 |
| phase2-r3-rev2 (accepted) | 2/3 | 3/3 |
| **phase2-r3-askfix** | **3/3** | **3/3** |

Both roles closed in every pass post-fix — pulling `RUNTIME_RULES.md` out of the coding catalog
freed up selector attention/budget rather than costing it anything, consistent with the token
and pack-size numbers above.

## `/wiki/ask` regression verification (Finding P2)

Live request against a fresh instance (same server used for the eval above), before the eval run:

```
POST /wiki/ask
{"question": "What changed for FoodEx2 in the 2024 maintenance release?", "max_pages": 6}
```

Result: `maintenance-2024.md` appears in `pages_used` and is the sole entry in `citations`. The
selector's own `tool_trace` (not graph expansion) shows it selected `maintenance-2024.md`
directly — proof the ask-scope catalog restored discoverability of non-prompt-facing pages.
Graph expansion then added `maintenance-history.md`, `maintenance-2023.md`, and
`facet-coding-rules.md` as summary-only neighbors (expected, unrelated to the fix). Full
response detail is recorded in the askfix report
(`.superpowers/sdd/askfix-report.md`).
