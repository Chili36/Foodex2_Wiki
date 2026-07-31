# Wiki-Ask Gold Set

Regression guard for the `/wiki/ask` endpoint's page selector, which uses the
"ask" catalog scope (`WikiStore.selector_catalog(scope="ask")` in
`wiki_api/wiki_store.py`). Unlike `/wiki/context-pack` (scope `"coding"`), the
ask scope must be able to select non-prompt-facing pages -- maintenance
history, orientation docs, `log.md` -- because ask questions are not limited
to "build me a code" requests. PR #37 regressed exactly this: a narrowing of
the ask catalog made maintenance questions silently fail. This gold set exists
so that regression is visible in CI/eval runs instead of only in production.

This is a **small, focused regression guard**, not a statistically expanded
ground truth set like `evals/selection/`. It reuses the same three-tier label
schema and the same scorer (`wiki_api/selection_scoring.py`) so the two evals
share plumbing, but the ask set intentionally stays at 8 cases: one per
regression surface, not broad statistical coverage.

`gold_cases.json` shape: `{"version": 1, "cases": [ ... ]}` -- identical shape
to `evals/selection/gold_cases.json`, except each case's `request` is the
`/wiki/ask` request body (`question`, `max_pages`) rather than the
context-pack selector payload.

## Case Schema

```json
{
  "id": "ASK-0001",
  "source": "regression-anchor:PR-37",
  "reviewed": true,
  "request": {
    "question": "What changed for FoodEx2 in the 2024 maintenance release?",
    "max_pages": 6
  },
  "labels": {
    "must_have": ["maintenance-2024.md"],
    "acceptable": ["maintenance-history.md", "..."],
    "must_not": ["pesticides-foodex2.md", "..."],
    "notes": "Why each tier was assigned, per the labeling rubric."
  }
}
```

All 8 cases are `"reviewed": true`. Unlike `evals/selection/`, these labels
are **controller-reviewed regression anchors**, not statistically expanded
ground truth drawn from a large sampled corpus -- each case was hand-picked to
exercise one specific ask-scope behavior (maintenance recall, orientation
recall, coding-question recall, or over-eager selection) and reviewed for
correctness against the actual wiki pages, not derived from a labeling budget
or inter-rater process.

## Labeling Rubric

Same three-tier schema and same tier-decision question as
`evals/selection/README.md` rubric rule 6: *would a competent answer be wrong
or ungrounded without this page?* Yes -> `must_have`. On-topic but not
required -> `acceptable`. Should never be selected for this question ->
`must_not` (supports `fnmatch` globs).

Because `/wiki/ask` scope intentionally includes maintenance and orientation
pages, the context-pack rubric's blanket "maintenance/orientation always
must_not" rules (rules 3-4) do **not** apply here -- those pages are must_have
exactly when the question is about them (ASK-0001, ASK-0002, ASK-0003), and
must_not otherwise (ASK-0004 through ASK-0008 exclude them so the eval also
catches over-eager selection, not just under-reach).

`index.md` and `RUNTIME_RULES.md` are excluded from scoring by the shared
scorer's `ALWAYS_PRESENT` set; do not label them.

## Case Coverage

| id | surface | must_have |
| --- | --- | --- |
| ASK-0001 | canonical regression case (maintenance, specific year) | `maintenance-2024.md` |
| ASK-0002 | maintenance/history, whole timeline | `maintenance-history.md` |
| ASK-0003 | orientation/architecture (ingest workflow) | `INGEST_WORKFLOW.md` |
| ASK-0004 | coding-flavored: implicit vs explicit facets | `implicit-vs-explicit-facets.md` |
| ASK-0005 | coding-flavored: packaging vs process facets | `packaging-facets.md` |
| ASK-0006 | coding-flavored: VMPR non-food matrices | `vmpr-foodex2.md` |
| ASK-0007 | no-clear-page (off-topic question) | none; `must_not` guards overlays/maintenance |
| ASK-0008 | coding-flavored: multi-facet code string syntax | `code-string-format.md`, `ingredient-facets.md` |

## Running

```
python scripts/selection_eval.py \
  --endpoint ask \
  --gold-path evals/ask/gold_cases.json \
  --label ask-baseline \
  --selector-model claude-sonnet-5 \
  --only-reviewed \
  --repeats 3
```

Use `--selector-model` to run a same-gold model comparison without restarting
the service or changing its configured default.

`--endpoint ask` POSTs `/wiki/ask/select-pages` instead of `/wiki/context-pack`,
scores `pages_used` against the same three-tier labels, records selector token
usage, and skips the context-pack-only `skeleton_enforcement`/backfill metrics.
The selector-only endpoint never invokes graph expansion or the answerer. Results land in
`reports/ask-evals/<date>-<label>/results.json`.

## Scoring semantics: selector only

The runner uses `/wiki/ask/select-pages`, so `pages_used` contains only selector
picks. Graph expansion and answer synthesis are separate mechanisms and incur no
calls during this eval.

The runner refuses more than 3 repeats unless `--allow-high-repeats` is supplied,
and aborts before network traffic when `cases × repeats` exceeds
`--max-estimated-calls` (default 200). Use `--dry-run` to inspect the budget without
making calls or writing a report.
