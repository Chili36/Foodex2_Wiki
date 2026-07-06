# Wording-Control Arm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether wording alone (three `select_when` hints + one guidance sentence) closes the Phase 3 systematic recall ceiling, measured on the 39-case set at repeats=5, with a one-revision cap.

**Architecture:** Pure wording changes to three page hints and the Selector Guidance completeness rubric; one full eval run + verdict triage against phase3-baseline. Spec: `docs/superpowers/specs/2026-07-05-wording-control-arm-design.md` (read it — the evidence and acceptance live there).

**Tech Stack:** Markdown edits; existing eval runner.

## Global Constraints

- Wording ONLY: the three named pages' `select_when` + one Completeness Rubric sentence in `selection-policy.md`. No code, no policy YAML, no gold labels, no new pages, no model names.
- Bright line: situation/scope phrasing; no query keywords, no filenames inside hints; ≤400 chars per hint (doctor-enforced).
- Acceptance (spec): Pattern A pairs (SEL-0017/0024/0025 × code-string-format) and Pattern B pairs (SEL-0038/0039 × validation-rules) leave `systematic`; no new systematic pairs; precision median ≥ 0.92; recall > 0.8923; leak-free 1.0; tokens ≤ 3,836; doctor + suite green.
- Iteration cap: ONE revision round. Ceiling survives → verdict "wording cannot close it" (a valid control result), stop.

---

### Task 1: Revise the three hints + guidance sentence

**Files:**
- Modify: `raw/efsa-guidance/code-string-format.md`, `raw/efsa-guidance/validation-rules.md`, `raw/efsa-guidance/business-rules.md` (frontmatter `select_when` only)
- Modify: `raw/efsa-guidance/selection-policy.md` (one sentence in `### Completeness Rubric`)

**Steps:**
- [ ] Read each target page fully plus the failing cases (SEL-0017/0024/0025/0034/0038/0039 in `evals/selection/gold_cases.json`) to ground the rewrites.
- [ ] Rewrite the three `select_when` hints per the spec's diagnosis (output-shape framing for code-string-format; Practical Dataset Checks scope for validation-rules; rule-identity/severity authority for business-rules). Complete sentences, ≤400 chars, bright line.
- [ ] Add one sentence to the Completeness Rubric: the pack must serve the code the coder will produce — constructions carrying explicit facet segments need assembly-syntax and dataset-review coverage, not only concept pages.
- [ ] Run `python -m wiki_api.doctor` (clean) and `.venv/bin/python -m pytest -q` (green; the guidance loader test asserts section presence, not exact text).
- [ ] Optional lint sanity pass on the three pages (`python -m wiki_api.llm_lint --page <p> --focus "select_when: situation phrasing, bright line, accuracy"`).
- [ ] Commit: `feat: reframe selection hints toward output-shape needs (wording-control arm)`

### Task 2: Wording-arm eval + verdict

**Files/outputs:**
- Output: `reports/selection-evals/<date>-phase4-wording-arm/{results.json,triage.md}`; Modify: `log.md`

**Steps:**
- [ ] Start own API instance (`.venv/bin/python -m uvicorn wiki_api.app:app --port 8015`; probe `trace.skeleton_enforcement`; stop it after).
- [ ] Run: `python scripts/selection_eval.py --label phase4-wording-arm --only-reviewed --repeats 5 --base-url http://127.0.0.1:8015` (195 calls).
- [ ] Score against the spec's acceptance. If missed: ONE revision round of the same wording surfaces (label `phase4-wording-arm-rev1`), then stop regardless.
- [ ] Write `triage.md`: medians vs phase3-baseline, miss-frequency comparison table (the 9 systematic pairs then vs now), threshold-adjacent re-confirmation (SEL-0026/0039/0020/0028), new systematic pairs if any, **the arm verdict** — CLOSED (wording sufficed; no mechanism needed now) or NOT CLOSED (mechanism phase justified; say which patterns survived). Honest caveats.
- [ ] `log.md` entry (`maintenance`): what changed, arm verdict, numbers.
- [ ] Doctor + suite green; commit: `feat: record wording-control arm verdict vs phase3 baseline`

## Self-Review Notes
Spec coverage: both scope items in Task 1; measurement/acceptance/cap/verdict in Task 2. No mechanism task — by design.
