# Phase 4 Wording-Control Arm — Run 1 Triage (phase4-wording-arm, repeats=5)

Run: `scripts/selection_eval.py --label phase4-wording-arm --only-reviewed --repeats 5`
against a fresh `.venv/bin/python -m uvicorn wiki_api.app:app --port 8015` instance
(`trace.skeleton_enforcement` probe confirmed before the run; instance stopped after).
39 reviewed cases × 5 passes, Task-1 wording as merged (output-shape `code-string-format`
hint, Practical-Dataset-Checks `validation-rules` scope, business-rules authority language,
one Completeness Rubric sentence).

**This is the first of the arm's two runs. The full then-vs-now tables, the revision round,
the threshold-adjacent re-confirmation, and the ARM VERDICT (NOT CLOSED — mechanism phase
justified) live in `reports/selection-evals/2026-07-06-phase4-wording-arm-rev1/triage.md`.**

## Headline result

| Metric | phase3-baseline | this run | Bar |
| --- | --- | --- | --- |
| Mean must-have recall | 0.8923 | **0.8731** (0.8453–0.8838) | > 0.8923 — FAILED |
| Mean precision | 0.9420 | 0.9524 (0.9469–0.9589) | ≥ 0.92 — passed |
| Leak-free rate | 1.0 | 1.0 | passed |
| Backfill case rate | 0.1795 | **0.2821** | (watch) — worse |
| Mean selector tokens | 3486.6 | 3559.8 | ≤ 3,836 — passed |

- **All five Pattern A/B target pairs fully closed**: SEL-0017/0024/0025 ×
  `code-string-format.md` and SEL-0038/0039 × `validation-rules.md` picked 5/5 each
  (0/5 in phase3).
- **But 11 NEW systematic pairs appeared** — `term-type-facet-constraints.md` missed ≥4/5 in
  8 cases (SEL-0017/0019/0020/0021/0024/0025/0026/0027), `implicit-vs-explicit-facets.md` in
  SEL-0027/0038, `process-validation-rules.md` in SEL-0005.
- Cause, verified in pass data: **displacement under the fixed pack budget**. The widened
  csf hint fired in 31/39 distinct cases, taking one of ~6 selector slots almost everywhere;
  ttfc/ivef fell out, and because the validation *role* stayed covered, the failsafe never
  backfilled them.
- SEL-0034 × `business-rules.md` stayed 0/5 (pvr picked 5/5 instead), SEL-0029 fcr 0/5,
  SEL-0026 ivef 1/5 — untouched by this run's wins.

Outcome: acceptance FAILED (recall below bar, new systematic pairs). The ONE permitted
revision round was used — csf gate tightened toward multi-segment constructions, rubric
sentence softened — and measured as `phase4-wording-arm-rev1`. See the rev1 triage for the
verdict.
