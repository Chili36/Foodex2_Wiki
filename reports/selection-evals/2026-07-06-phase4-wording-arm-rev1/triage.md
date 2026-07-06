# Phase 4 Wording-Control Arm — Final Triage & Verdict (rev1, 2026-07-06)

Design: `docs/superpowers/specs/2026-07-05-wording-control-arm-design.md`.
Reference: `reports/selection-evals/2026-07-05-phase3-baseline/` (39 reviewed cases, repeats=5).
This file is the arm's verdict document; it covers **both** measurement runs:

- **Run 1 (`2026-07-05-phase4-wording-arm/`)** — Task 1 wording as merged: output-shape
  `select_when` on `code-string-format.md` ("explicit facet segments — one or many"),
  Practical-Dataset-Checks scope on `validation-rules.md`, rule-identity/severity authority
  on `business-rules.md`, one Completeness Rubric sentence in `selection-policy.md`.
  Fresh instance on port 8015, `skeleton_enforcement` probe confirmed, instance stopped after.
- **Run 2 / rev1 (this directory)** — the ONE permitted revision round (same wording surfaces
  only): `code-string-format.md` gate tightened from "one or many" to multi-segment
  constructions; the rubric sentence softened to "in addition to — never instead of — the
  term-type and facet-legality coverage every construction needs". `validation-rules.md` and
  `business-rules.md` hints untouched from run 1. Fresh instance on port 8016, probe
  confirmed, instance stopped after. **Iteration cap reached — no further rounds.**

## Metric medians (min–max), all three runs

| Metric | phase3-baseline | phase4-wording-arm | phase4-wording-arm-rev1 | Acceptance bar |
| --- | --- | --- | --- | --- |
| Mean must-have recall | **0.8923** (0.8880–0.9222) | 0.8731 (0.8453–0.8838) | 0.8795 (0.8709–0.9137) | > 0.8923 — **FAILED both runs** |
| Mean precision | 0.9420 (0.9335–0.9454) | 0.9524 (0.9469–0.9589) | 0.9469 (0.9249–0.9536) | ≥ 0.92 — passed both |
| Leak-free rate | 1.0000 | 1.0000 | 1.0000 | = 1.0 — passed both |
| Backfill case rate | 0.1795 | 0.2821 | 0.1795 | (watch) |
| Mean selector tokens | 3486.6 | 3559.8 | 3587.1 | ≤ 3,836 — passed both |
| Mean pack chars | 20,127 | 19,729 | 20,573 | — |

Old-15 subset mean recall per pass: run 1 = 0.9833/0.95/0.9833/0.95/0.95; rev1 =
0.9111/1.0/0.9667/0.9667/1.0 (phase3: 1.0 ×3, 0.9833 ×2). The wording changes leaked
variance into the previously-stable old set in both runs.

## The 9 phase3 systematic pairs, then vs now (page picked, out of 5 passes)

| Case | Page | phase3 | run 1 (arm) | rev1 | Status after rev1 |
| --- | --- | --- | --- | --- | --- |
| SEL-0017 | code-string-format.md | 0/5 | **5/5** | 0/5 | **REOPENED** |
| SEL-0024 | code-string-format.md | 0/5 | **5/5** | 1/5 | **REOPENED** |
| SEL-0025 | code-string-format.md | 0/5 | **5/5** | 0/5 | **REOPENED** |
| SEL-0026 | implicit-vs-explicit-facets.md | 1/5 | 1/5 | 1/5 | unmoved (untargeted) |
| SEL-0029 | facet-coding-rules.md | 0/5 | 0/5 | 0/5 | unmoved (untargeted) |
| SEL-0034 | business-rules.md | 0/5 | 0/5 | 0/5 | **unmoved despite targeted rewrite** |
| SEL-0038 | validation-rules.md | 0/5 | **5/5** | **5/5** | **CLOSED (durable)** |
| SEL-0039 | validation-rules.md | 0/5 | **5/5** | **5/5** | **CLOSED (durable)** |
| SEL-0039 | term-type-facet-constraints.md | 1/5 | 0/5 | 0/5 | worse |

- **Pattern A (load-bearing) oscillated, did not converge.** The wide output-shape gate
  ("one or many" segments) closed all three pairs at 5/5 — but fired in **31 of 39** distinct
  cases (mostly 5/5), consuming a selector slot almost everywhere. The tightened multi-segment
  gate collapsed to 0–1/5 in the three cases that *need* it while still firing 3–5/5 in
  SEL-0006/0014/0021/0032/0033 — all cases where csf is merely *acceptable* because the query
  itself surfaces a code string. The selector picks the page when the **query** shows the
  artifact, not when the **output** demands it; no wording of the gate makes the multi-segment
  condition verifiable from the request. This is the phase3 "situational inference" diagnosis
  reproduced under two opposite wordings.
- **Pattern B closed durably.** The Practical-Dataset-Checks scope addition held 5/5 across
  both runs (hint untouched between them). This is the arm's one genuine, keepable win — it
  was also the already-recorded P2 lint gap, i.e. a missing-scope defect, not a ceiling case.
- **SEL-0034 is wording-immune.** `process-validation-rules.md` was picked 5/5 in *both* runs
  as the reconstitution authority; the sharpened business-rules authority language changed
  nothing. Consistent with label-review candidate #1 (pvr is a defensible route to the same
  rule); whatever the label decision, hint wording does not move this pair.

## New systematic pairs vs phase3 (the displacement dynamic)

**Run 1: 11 new systematic pairs** — `term-type-facet-constraints.md` missed ≥4/5 in
SEL-0017/0019/0020/0021/0024/0025/0026/0027 (8 cases), `implicit-vs-explicit-facets.md` in
SEL-0027/0038, `process-validation-rules.md` in SEL-0005. Backfill case rate rose
0.1795 → 0.2821.

**Rev1: 3 new systematic pairs** — SEL-0019 ttfc 5/5, SEL-0028 ttfc 4/5, SEL-0038 ivef 4/5.
Backfill returned to 0.1795.

Mechanism, verified in the pass data: packs are capped at 8 pages, of which
`RUNTIME_RULES.md` + `index.md` are fixed — ~6 selector slots. In run 1 csf occupied a slot in
31/39 cases and ttfc/ivef fell out; the validation *role* stayed covered (structural-validation
/ csf / pvr), so the role-level failsafe never fired and the misses stand — exactly the
role-covered-but-wrong-page failure phase 2 predicted, now *induced by a recall fix*. In rev1
the SEL-0038/0039 packs show the same trade at case level: `validation-rules.md` in (5/5), and
the displaced page is the case's *other* must_have (ivef missing 4/5 in SEL-0038, ttfc 5/5 in
SEL-0039 — worse than phase3's 4/5). **Closing one must_have by strengthening its hint pushes
out another must_have; the hints compete for a fixed budget.**

## Threshold-adjacent re-confirmation (from the phase3 caveats; picked/5)

| Pair | phase3 | run 1 | rev1 | Reading |
| --- | --- | --- | --- | --- |
| SEL-0026 ivef | 1/5 | 1/5 | 1/5 | confirmed systematic (4/5 missed in all three runs) |
| SEL-0039 ttfc | 1/5 | 0/5 | 0/5 | confirmed and hardened (now 5/5 missed) |
| SEL-0020 ttfc | 2/5 | 1/5 | 3/5 | flip-flops across the systematic threshold with wording noise |
| SEL-0028 ttfc | 2/5 | 4/5 | 1/5 | flip-flops (stochastic → fine → systematic) |

SEL-0020/0028 ttfc are wording-sensitive noise riding the displacement dynamic; SEL-0026 ivef
and SEL-0039 ttfc are real.

## Acceptance scorecard (spec §Measurement, applied to the final config = rev1)

1. Pattern A pairs picked ≥2/5: **FAILED** (0/5, 1/5, 0/5). Pattern B: passed (5/5, 5/5).
2. No new systematic pairs: **FAILED** (3; run 1 had 11).
3. Recall > 0.8923: **FAILED** (0.8795; run 1: 0.8731). Precision ≥0.92, leak-free 1.0,
   tokens ≤3,836: all passed in both runs.
4. Doctor clean, suite green (106 passed): passed.

## ARM VERDICT: **NOT CLOSED — mechanism phase justified**

(Read precisely: *partially* closed at the pattern level — Pattern B is a durable wording
win worth keeping — but the arm's question was whether wording alone closes the systematic
within-role ceiling, and the answer is no. Both configurations failed the acceptance bar.)

Evidence, exactly:

- The two runs are the two halves of an oscillation, not steps of a convergence: wide gate =
  Pattern A closed (15/15 picks) + 11 displacement pairs + recall 0.8731; narrow gate =
  Pattern A reopened (1/15 picks) + 3 residual displacement pairs + recall 0.8795. Neither
  side beats the phase3 recall median of 0.8923.
- The binding constraint is structural, not lexical: ~6 free slots per pack, ttfc must_have in
  34/39 cases, and hint strengthening reallocates slots among must_haves instead of adding
  coverage. A hint rewrite cannot express "this page is needed *in addition to* the pages the
  query already suggests" when the selector's budget is already spent.
- Two pairs are wording-immune outright: SEL-0034 (pvr picked 5/5 under both business-rules
  hint versions) and Pattern A's gate (fires on query-visible code strings under both
  versions, never on output-inferred ones).

**Implication for the mechanism phase** (per the phase3 triage's option 2): this data
specifically favours **finer-grained roles** — the failure in every surviving pair is
role-covered-but-wrong-page, and the displacement dynamic shows the selector cannot trade
slots correctly *within* the coarse validation/facet roles. Splitting the validation role
(structural / business-severity / review-level) and guaranteeing term-type coverage as its own
role would make the failsafe catch exactly the misses this arm induced and could not fix. A
bounded completeness-critic pass remains the fallback; token reference cost is now
~3,587/case (still ≤ 1.03× phase3). Pattern B's hint fix and the softened rubric sentence
should be kept regardless.

## Honest caveats

- **The committed wording (rev1) is a slight net regression vs phase3 on this instrument**:
  recall median 0.8795 vs 0.8923 (pass ranges overlap: 0.8709–0.9137 vs 0.8880–0.9222),
  10 systematic pairs vs 9, with a different mix (B closed, +3 displacement). It also carries
  the durable Pattern B win. Keeping vs reverting the csf hint + rubric sentence is David's
  call; the validation-rules hint should be kept either way.
- Single selector model (claude-sonnet-4-6), single day per run; rev1 ran on 2026-07-06,
  the other two runs on 2026-07-05.
- The SEL-0034 conclusion ("wording-immune") is entangled with label-review candidate #1 —
  if pvr is promoted to co-must_have-alternative, the pair leaves the scoreboard entirely.
- Run 1's precision gain (0.9524) is partly an artifact: csf over-firing landed on
  acceptable-tier cases, so precision did not punish the displacement that recall did. The
  Task-1 review's precision watch (≥0.92) was the wrong tripwire for this failure mode; the
  new-systematic-pairs gauge caught it.
- The rubric-sentence soften and the csf-gate tighten were changed together in the one
  permitted round, so their individual contributions to the displacement reduction
  (11 → 3 pairs) are not separable from this data.

## Addendum: budget probe & adoption (2026-07-06)

David's hypothesis — that the fixed `max_pages=7` budget, not hint quality, drove the
displacement — was tested directly: run-1 (strong) wording re-run at `max_pages=9`
(`reports/selection-evals/2026-07-06-phase4-budget-probe9/`, 5 repeats, override verified
via pack-size distribution).

| median of 5 | phase3 baseline (7) | strong wording @7 | strong wording @9 |
| --- | --- | --- | --- |
| must-have recall | 0.8923 | 0.8731 | **0.9380** |
| systematic pairs | 9 | 16 | **4** |
| backfill_case_rate | 0.1795 | 0.2821 | **0.1282** |
| precision | 0.9420 | 0.9524 | 0.9480 |
| selector tokens | 3487 | 3560 | 3572 |
| mean pack chars | ~18.8k | ~18.8k | ~23.2k |

Verdict revision: the arm's NOT CLOSED stands for wording-at-budget-7, but the budget
probe shows wording+budget together CLOSE the displacement dynamic: all 5 Pattern A/B
targets remain closed with no displacement. Remaining rump: 4 pre-existing systematic
pairs (SEL-0027/0039 ttfc; SEL-0029 fcr; SEL-0034 br — the wording-immune sibling
competitions). **Decision (David, 2026-07-06): adopt `max_pages=9` as the context-pack
default** (run-1 wording restored), accepting ~+1.1k tokens/pack downstream cost and the
selector's observed drift toward cap−1 (packs typically carry 8 pages). Gold-case
requests aligned to the new production default. The selection chapter closes here: no
mechanism phase; the 4-pair rump is accepted (recall 0.938 with the deterministic
failsafe floor). Next investment shifts to wiki content.
