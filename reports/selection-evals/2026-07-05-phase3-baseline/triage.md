# Phase 3 Baseline Triage — 2026-07-05 (phase3-baseline, repeats=5)

Run: `scripts/selection_eval.py --label phase3-baseline --only-reviewed --repeats 5`
against a fresh `.venv/bin/python -m uvicorn wiki_api.app:app --port 8014` instance started
for this task (probe confirmed `trace.skeleton_enforcement` present before the run; instance
stopped after). 39 reviewed cases × 5 passes = 195 selector calls. This is the first run on
the expanded gold set (15 original + 24 new: 13 DMT-mined no-domain cases with official codes,
11 synthetic coverage/floor cases), and the first measurement of the selector on the four
previously-untested pages (`structural-validation.md`, `validation-rules.md`,
`business-rules.md`, `code-string-format.md`).

**The question this report answers: is there a systematic within-role recall ceiling?**

**Answer: YES.** Nine (case, page) pairs are systematic (missed in ≥ 4/5 passes), concentrated
on three recurring pages across multiple cases. Details and exact pairs below.

## Metric medians (min–max across the 5 passes)

| Metric | phase3-baseline (39 cases) |
| --- | --- |
| Mean must-have recall | **0.8923** (0.8880–0.9222) |
| Mean precision | **0.9420** (0.9335–0.9454) |
| Leak-free rate | **1.0000** (1.0–1.0) |
| Backfill case rate | **0.1795** (0.1538–0.2308) |
| Mean backfills/case | **0.1795** (0.1538–0.2564) |
| Mean selector tokens | **3486.6** (3480.2–3502.6) |
| Mean pack chars | **20,127** (20,049–20,703) |

**Do not compare these rates to phase2 numbers.** The expanded set changes the denominator:
24 of 39 cases are new, harder by design (no-domain mined cases with empty `candidate_hints`,
adversarial validation floor-fillers), and 9 of them exist specifically to exercise pages the
old set never tested. The drop from the phase2-r3-askfix reference (recall median 1.0,
backfill 0.0 on the old 15-case set) is the instrument getting sharper, not a regression —
and the data supports that framing directly: **the original 15 cases score mean recall 1.0 in
3 of 5 passes and 0.9833 in the other two** (the only old-set miss is SEL-0005
`process-validation-rules.md`, 2/5 passes — the same at-the-bar variance phase2 documented).
Every systematic miss is on a new case. Leak-free stayed at 1.0 across all 195 calls, and
selector token cost is flat (~3487/case vs ~3458 reference) despite the harder queries.

## Full miss-frequency table

Systematic threshold at repeats=5: missed in ≥ ceil(2/3 × 5) = 4 passes.

| Case | Missing must_have page | Missed | Class |
| --- | --- | --- | --- |
| SEL-0017 | code-string-format.md | 5/5 | **systematic** |
| SEL-0024 | code-string-format.md | 5/5 | **systematic** |
| SEL-0025 | code-string-format.md | 5/5 | **systematic** |
| SEL-0026 | implicit-vs-explicit-facets.md | 4/5 | **systematic** |
| SEL-0029 | facet-coding-rules.md | 5/5 | **systematic** |
| SEL-0034 | business-rules.md | 5/5 | **systematic** |
| SEL-0038 | validation-rules.md | 5/5 | **systematic** |
| SEL-0039 | validation-rules.md | 5/5 | **systematic** |
| SEL-0039 | term-type-facet-constraints.md | 4/5 | **systematic** |
| SEL-0005 | process-validation-rules.md | 2/5 | stochastic |
| SEL-0017 | term-type-facet-constraints.md | 1/5 | stochastic |
| SEL-0020 | term-type-facet-constraints.md | 3/5 | stochastic |
| SEL-0022 | term-type-facet-constraints.md | 1/5 | stochastic |
| SEL-0026 | term-type-facet-constraints.md | 1/5 | stochastic |
| SEL-0027 | facet-coding-rules.md | 1/5 | stochastic |
| SEL-0027 | implicit-vs-explicit-facets.md | 3/5 | stochastic |
| SEL-0027 | term-type-facet-constraints.md | 1/5 | stochastic |
| SEL-0028 | term-type-facet-constraints.md | 3/5 | stochastic |
| SEL-0035 | business-rules.md | 2/5 | stochastic |
| SEL-0035 | term-type-facet-constraints.md | 1/5 | stochastic |
| SEL-0036 | business-rules.md | 3/5 | stochastic |
| SEL-0037 | ingredient-facets.md | 3/5 | stochastic |
| SEL-0038 | implicit-vs-explicit-facets.md | 1/5 | stochastic |

## THE GATE ANSWER: systematic within-role ceiling — YES

Specific non-default pages appear in `systematic_misses` across multiple cases. The nine
systematic (case, page) pairs group into three recurring patterns:

### Pattern A — output-syntax blindness: `code-string-format.md` (3 cases, 15/15 misses)

- SEL-0017 (fortified low-fat milk → official code carries 4 facet segments): 0/5 picks.
- SEL-0024 (sausage stroganoff → 8-segment code, seven F04 + F22): 0/5 picks.
- SEL-0025 (savoiardi biscuits → 6-segment code): 0/5 picks.

The selector never allocates a slot for final code-string assembly. The need is invisible in
the query text — it only follows from reasoning forward to the *shape of the code the coder
will build* (many descriptors → many `#`/`$` segments → syntax rules matter). The selector's
completeness rubric covers "how the construction will be validated" but nothing pushes it to
cover "how the final string is assembled." Notably it *did* pick the page 3/5 in SEL-0029,
where the query itself quotes a malformed code string — confirming the gap is situational
inference, not page invisibility.

### Pattern B — orientation/review-level validation loses to specific validation pages:
`validation-rules.md` (2 of its 3 must_have cases, 10/10) and `business-rules.md` (1
systematic + 2 stochastic of its 3 must_have cases)

- SEL-0038 (same-nature mixed berries, F27-vs-F01 — decided by validation-rules' practical
  dataset-review check): validation-rules 0/5.
- SEL-0039 (herb infusion, dry-material-vs-beverage ambiguity — flagged by the same practical
  checks): validation-rules 0/5, and term-type-facet-constraints 1/5.
- SEL-0034 (adding reconstitution to a dried powder — BR28 severity is the deciding
  authority): business-rules 0/5; the selector picked `process-validation-rules.md` 5/5
  instead (see label-review candidates).
- SEL-0035 / SEL-0036 (deprecated-term and raw-base-powder BR questions): business-rules
  missed 2/5 and 3/5 — same page, below the systematic threshold.

This is the failure shape phase 2 predicted and recorded as Phase 3 evidence: the role-level
failsafe guarantees *a* validation page, not *the* one. In every one of these case-passes the
validation role was covered (by structural-validation, process-validation-rules, or ttfc), so
no backfill fired and the miss stands. A contributing cause is already on file: the phase2
lint (P2, left unfixed by design) found `validation-rules.md`'s `select_when` omits its
Practical Dataset Checks scope — exactly the content SEL-0038/0039 turn on.

### Pattern C — hidden-difficulty single cases (systematic but not page-recurring)

- SEL-0026 `implicit-vs-explicit-facets.md` 4/5 missed: the case's real difficulty (detailed
  term missing → generic base + F26.A07XE marker) is carried by the official DMT code, not
  the query text ("Saftsoppa"); the selector consistently read it as a soup/ingredient case
  (ingredient-facets 5/5, unlabeled).
- SEL-0029 `facet-coding-rules.md` 5/5 missed: the duplicate-facet repair case; the selector
  treated it as pure validation repair (structural-validation 5/5 — the designed target,
  which it *did* get) and skipped facet-family mapping. It also skipped the base_term role
  outright in 4/5 passes (failsafe backfilled `base-term-selection.md`).

### Failsafe-masked systematic selector omissions (visible in backfills, not in miss counts)

The miss-frequency table understates the selector-level ceiling because the Phase 1 failsafe
repairs role-empty packs before scoring. Systematic backfills this run: SEL-0036 and SEL-0037
`base-term-selection.md` 5/5, SEL-0029 4/5 (the adversarial validation-question cases make
the selector skip the base_term role entirely); SEL-0035 `facet-coding-rules.md` 5/5;
SEL-0014 `base-term-selection.md` 5/5 (pre-existing, old set). The mechanism works as
designed — but a recall fix should be measured at the selector level, with backfills visible,
exactly as this runner reports them.

### Recommendation (gated, not built here)

Recommend a follow-up mechanism phase, measured against this gold set with `--repeats 5` and
the miss-frequency instrument as the acceptance gauge. Ordered cheapest-first, honouring the
token-economy constraint and the no-case-specific-rules bright line:

1. **Wording round first** (phase-2-style, bounded revisions): fix the known
   `validation-rules.md` hint gap (Practical Dataset Checks scope — an already-recorded P2
   lint finding) and re-anchor `code-string-format.md`'s hint on the *situation* (a code that
   will carry several facet segments) rather than the artifact. This may close Pattern B and
   part of A for zero runtime tokens. Phase 2's history warns wording alone saturates; treat
   this as the control arm, not the fix.
2. **If wording doesn't close it: a completeness mechanism that reasons about the expected
   output-code shape** — the recurring theme in all three patterns is that the missing pages
   are needed by the *code the coder will produce* (multi-segment syntax, review checks,
   BR severities), not by the query text. Candidates: a finer-grained role model
   (e.g. splitting "validation" into structural/business/review coverage) or a bounded
   completeness-critic pass. Any loop must carry an explicit token budget; the current
   ~3487 tokens/case is the reference cost.

Do NOT build either in this phase — that is the gate's design.

## Per-case notes (systematic cases)

- **SEL-0017/0024/0025** (Pattern A): otherwise near-perfect packs — all other must_haves
  present 4–5/5; the only stable defect is the missing syntax page. Recall pinned at 0.75.
- **SEL-0026**: recall median 0.667; one pass hit 1.0 (the single ivef pick), one 0.333.
  The selector's alternative reading (composite soup → ingredient-facets) is consistent
  across passes; ttfc was backfilled once.
- **SEL-0029**: recall constant 0.667 across all 5 passes — got the designed target
  (structural-validation 5/5) but never the facet-repair page; heavy unlabeled padding
  (process-validation-rules 5/5, process-facets 5/5) drawn by the "frozen/freezing-facet"
  wording.
- **SEL-0034**: recall constant 0.667; process-validation-rules picked 5/5 (acceptable tier)
  as the de facto reconstitution authority instead of business-rules.
- **SEL-0038**: recall stable 0.8 (0.6 once); everything present except validation-rules;
  pesticides overlay correctly picked 5/5 (domain-signal handling works).
- **SEL-0039**: worst case in the set — recall median 0.333 (both validation must_haves
  missing plus heavy unlabeled process-page padding: the selector read "infusion" as a
  processing problem, not a base-term-identity problem).

## Label-review candidates (documented, not edited)

The following look like defensible selector behaviour that the labels currently punish; David
may want to re-tier them. No labels were changed in this run.

1. **SEL-0034 — `process-validation-rules.md` (currently acceptable) vs `business-rules.md`
   (must_have)**: the selector picked pvr 5/5; pvr's own hint covers "reconstitution limits",
   which is the case's exact question. The label argues BR28's severity is the deciding
   authority — defensible, but the selector's pick is a reasonable route to the same rule.
   Candidate: promote pvr to co-must_have-alternative or accept this as the intended
   distinction and let the mechanism phase target it.
2. **SEL-0029 — `process-facets.md` and `process-validation-rules.md` (currently unlabeled,
   picked 5/5 each)**: the case's own notes say candidate codes A0B9Z/A07JS are cited
   verbatim in `process-facets.md`; punishing that pick as a precision miss while the
   candidate hints point at the page is tension worth resolving (unlabeled → acceptable?).
3. **`process-facets.md` unlabeled-pick pattern generally**: 13 of 21 distinct unlabeled-pick
   pairs this run are process-facets, drawn by treatment words (stekt, torkad, infusion,
   fortified) in cases whose drafts left it untiered (SEL-0017 5/5, SEL-0027 5/5, SEL-0031
   5/5, SEL-0036 5/5, SEL-0039 5/5, …). The cross-check model independently called it
   acceptable for SEL-0017. A one-pass acceptable-tier review of process-facets across the
   new cases would make precision more honest.
4. **SEL-0026** (weaker candidate): implicit-vs-explicit is only inferable from the official
   DMT code, not from the request the selector sees. The label is correct about what a good
   pack needs; whether a selector *can* know it from this request is a fair question for the
   mechanism phase (this is precisely where candidate data / retrieval could help — the case
   has empty candidate_hints by design).

## Honest caveats

- **Denominator non-comparability (repeated on purpose)**: none of the summary rates in this
  report are comparable to phase1/phase2 reports; 24/39 cases are new and harder by design.
  The only valid cross-run comparison is the old-15 subset (recall 1.0 / 0.9833 — unchanged
  from phase2 within noise) and per-token cost (~flat).
- **New-case label quality**: the new labels were drafted by one model with full-page
  grounding, cross-checked by a hint-only second model (20 genuine disagreements, resolved by
  David in favour of the drafts, cross-check-only must_haves folded into acceptable). The
  systematic misses all sit on new cases, so label-quality risk and ceiling evidence are
  correlated — the four label-review candidates above are exactly the places to spend
  review time. Robustness, stated precisely (per the audit): the GATE VERDICT survives any
  single label falling — Pattern A (code-string-format) rests on 3 independently DMT-mined
  cases and remains multi-case under any single removal. Pattern B (validation-rules) rests
  on only 2 cases and would drop below page-recurrence if either SEL-0038 or SEL-0039 is
  re-tiered; treat B as supporting evidence, A as the load-bearing pattern.
- **Single-config, single-day run**: one selector model (claude-sonnet-4-6), one prompt
  configuration, 5 passes on one day. The systematic/stochastic split at 4/5 is robust for
  0/5-vs-5/5 pages (Patterns A and B are mostly 0/5 picks — as systematic as the instrument
  can say), but the 4/5 entries (SEL-0026 ivef, SEL-0039 ttfc) sit one pass from
  reclassification, and SEL-0020/SEL-0028 ttfc at 3/5 sit one pass *below* the threshold.
  Threshold-adjacent entries should be re-confirmed by the follow-up phase's own baseline.
- **Backfill masking**: mean recall benefits from failsafe backfills (SEL-0035/36/37 would
  otherwise show additional systematic must_have misses). The scoreboard measures the
  system as shipped, which is correct — but mechanism-phase deltas should also be read
  against the backfill table, not recall alone.
- **ttfc's long tail**: `term-type-facet-constraints.md` is must_have in 34 of 39 cases and
  shows scattered misses in 8 of them (one systematic, at 4/5). It is the page most exposed to the
  role-covered-but-wrong-page failure; any finer-grained role model should treat it as the
  primary regression watch.
