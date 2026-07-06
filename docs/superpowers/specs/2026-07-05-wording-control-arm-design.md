# Wording-Control Arm — Design

**Date:** 2026-07-05
**Phase:** 4 (control arm) of the page-selection improvement plan; prescribed by the Phase 3 gate triage (`reports/selection-evals/2026-07-05-phase3-baseline/triage.md`) and approved by David.
**Question this phase answers:** can *wording alone* (selection hints + selector guidance prose) close the systematic within-role ceiling, or is a mechanism warranted?

## Evidence being acted on (Phase 3, Opus-audited)

- **Pattern A (load-bearing):** `code-string-format.md` picked 0/5 in all 3 of its cases (SEL-0017/0024/0025). Its current `select_when` says "the case involves assembling or checking the final code string" — input vocabulary. No query says that; the need follows from the *output* (a multi-facet code) the coder will produce.
- **Pattern B (supporting):** `validation-rules.md` picked 0/5 in SEL-0038/0039. Its hint covers the two-layer/severity orientation but omits the **Practical Dataset Checks** scope (reconstitution/infusion ambiguity, same-nature mixed-commodity source handling) that both cases turn on.
- **SEL-0034:** `business-rules.md` lost 5/5 to sibling `process-validation-rules.md` on a reconstitution case — the hint doesn't assert its authority when rule identity/severity is the question.

## Scope (wording ONLY — the arm's definition)

1. Revise `select_when` on exactly three pages: `code-string-format.md` (reframe to output-shape situation: constructions carrying explicit facet segments need assembly syntax), `validation-rules.md` (add the Practical Dataset Checks scope), `business-rules.md` (sharpen rule-identity/severity authority vs the process sibling). Bright line holds: situation/scope phrasing, no query keywords, no filenames; ≤400 chars (doctor).
2. One sentence added to the **Completeness Rubric** in `selection-policy.md`'s Selector Guidance: consider the shape of the code that will be produced — constructions carrying explicit facets need assembly-syntax and dataset-review guidance, not only concept pages. (Guidance wording was in-scope for Phase 2's revision rounds; same category here.)
3. Nothing else: no code, no failsafe/policy-YAML change, no gold-label change, no new roles, no mechanism.

## Measurement & acceptance (vs phase3-baseline, same 39 cases, repeats=5)

1. **Primary:** Pattern A's three (case, page) pairs and Pattern B's two pairs leave `systematic` (each page picked in ≥2/5 passes per case; target ≥4/5).
2. No new systematic pairs introduced (watch for over-firing: the reframed code-string-format hint applies to many cases — precision median must stay ≥ 0.92).
3. Medians: recall > 0.8923 (misses closing must show up), leak-free 1.0, tokens ≤ 1.1 × 3487 (≈ ≤ 3,836).
4. Doctor clean; suite green.

**Iteration cap:** ONE revision round of the same wording surfaces. If the ceiling survives after that, the arm's honest verdict is "wording cannot close it" — that is a *successful control result* justifying the mechanism phase (finer-grained roles or a bounded completeness critic, per the triage), not a failure to be tuned past.

**Threshold-adjacent re-confirmation (from the triage):** report what happens to SEL-0026 ivef, SEL-0039 ttfc (4/5), and SEL-0020/0028 ttfc (3/5) in the new run.

## Out of scope

Any completeness mechanism or role-model change; gold-label edits (the 4 label-review candidates stay documented, untouched); `/wiki/ask`; ride-along cleanups already noted for the mechanism phase.
