# Baseline Triage — 2026-07-05

Baseline: `scripts/selection_eval.py --label baseline --only-reviewed`, 15 reviewed cases.

| Metric | Value |
| --- | --- |
| Mean must-have recall | 0.73 |
| Mean precision | 0.91 |
| Leak-free rate | 0.93 (1 case leaked) |
| Mean pack size | ~16.0k chars |

## Miss tally (by page)

| Missing must-have page | Cases | Category | Gate |
| --- | --- | --- | --- |
| `term-type-facet-constraints.md` | SEL-0001,2,3,4,6,7,8,9,10,14 (**10/15**) | validation | Phase 1 |
| `process-validation-rules.md` | SEL-0005 | validation | Phase 1 |
| `base-term-selection.md` | SEL-0014 | base-term | Phase 1 |
| `facet-coding-rules.md` | SEL-0010, SEL-0012 | facet | Phase 1 / Phase 2 |
| `implicit-vs-explicit-facets.md` | SEL-0011 | facet (derivative-specific) | Phase 2 |

Leak: SEL-0009 pulled in `maintenance-2019.md` + `maintenance-2022.md` (a pesticides case; maintenance pages should never enter a coding pack).

## Interpretation

The dominant, unambiguous signal is a **whole-category miss of the validation layer**: `term-type-facet-constraints.md` is absent from 10 of 15 packs, and `process-validation-rules.md` from the one processed-food case. The selector reliably picks base-term and domain-overlay pages but treats validation pages as optional. This is exactly the pre-existing hypothesis (memory: page-selector-gaps) now quantified against ground truth.

Two structural facts make this a Phase 1 (deterministic skeleton) problem, not a prompt-tuning problem:

1. Whether a validation page is needed follows from page **category** + the fact that every context-pack case constructs a code — it does not depend on the query. A deterministic quota ("every code-construction pack carries ≥1 validation page, ≥1 base-term page, ≥1 facet page") closes the bulk of these misses without asking the LLM to re-derive the skeleton each call.
2. SEL-0014 missing `base-term-selection.md` — the single most fundamental page — shows the selector will drop even the base layer under distraction (a packaging composite). A skeleton floor prevents that.

The maintenance leak (SEL-0009) is the same shape from the other side: a deterministic drop rule (maintenance/orientation pages never enter a coding pack) removes it.

## Gate decision

- **Phase 1 (deterministic category skeleton): OPEN — highest priority.** Addresses the 10 validation misses, the process-validation miss, the base-term miss, the two bare facet-category misses, and the maintenance leak. Expected to move recall and leak-free rate materially with no precision collapse (skeleton pages are on-topic, so they land in must-have/acceptable, not leaks).
- **Phase 2 (candidate-aware selector): QUEUED behind Phase 1.** Two residual misses are candidate-signal, not category: SEL-0011 (`implicit-vs-explicit-facets.md` for a `termType: d` derivative candidate) and SEL-0012 (`facet-coding-rules.md` with a group-term candidate the coder must reject). These need the selector to read candidate termTypes — Phase 1's category floor will not pick the *specific* facet page, so re-measure after Phase 1 to confirm they persist before building Phase 2.
- **Phase 3 (recall backstop): not justified yet.** No vocabulary-mismatch misses survive once the category floor is in place — revisit only if Phase 1+2 leave gaps.
- **Label fixes: none.** SEL-0013 and SEL-0015 already score 1.0; no case shows a mislabeled must-have.

## Caveat

Single run per case; the selector is non-deterministic (LLM). Numbers are a point estimate, not a distribution. Before declaring a Phase 1 win, run the baseline 2–3× (or add a repeat flag) to bound variance on the borderline cases.
