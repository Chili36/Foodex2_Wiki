# Page Selection Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/wiki/context-pack` page selection measurable, then measurably better, so downstream tools (DMT and others) reliably receive the pages a FoodEx2 coder actually needs.

**Architecture:** Phase 0 builds a gold selection eval (labeled cases + deterministic scoring runner) so every later change is falsifiable. Phases 1–4 are evidence-gated improvements: deterministic category skeleton, selector-facing catalog metadata, recall backstop, and token budgeting. Only Phase 0 is planned in executable detail here; each later phase gets its own plan once its evidence gate opens.

**Tech Stack:** Python 3, FastAPI service in `wiki_api/`, pytest, existing eval conventions in `scripts/` + `reports/`.

## Global Constraints

- Never change any LLM model name without asking David first.
- Token economy is a first-class design constraint: every phase reports token cost alongside quality.
- No overfitting: no case-specific rules in wiki pages or selector prompts; failures drive general fixes (categories, metadata, policy), not per-food hacks.
- Policy lives in markdown, not service code: any new selection policy must be readable from a markdown page, with service code only enforcing it.
- Wiki API base URL default: `http://127.0.0.1:8010`.
- All work on feature branches; issues tracked on GitHub (`Chili36/Foodex2_Wiki`).

## Background (why)

Findings from the 2026-07-05 review (see conversation + issues for full detail):

1. Answer quality is evaluated (`reports/wiki-ask-evals/`), but page selection — the actual product of `/wiki/context-pack` — has no eval. Existing suite cases carry `reference_pages_from_run`, which is circular (labels captured from what a run selected).
2. Observed failures in existing run data: zero validation pages selected for code-construction cases; both `pesticides-foodex2.md` and `contaminants-foodex2.md` selected for a single-domain case; maintenance pages selected without any maintenance question.
3. The selector's only retrieval surface is `index.md` one-line summaries written in *content* vocabulary, not *when-to-select* vocabulary.
4. `candidate_hints` are passed to the selector but nothing tells it how to use them.
5. Budget is a page count, not a token budget; `RUNTIME_RULES.md` is prepended outside the budget.

## Phase Map

| Phase | Deliverable | Evidence gate to proceed |
| --- | --- | --- |
| 0 (this plan) | Gold selection set + deterministic eval runner + baseline report | none — start here |
| 1 | Deterministic category skeleton for context-packs | Baseline shows must-have recall gaps concentrated in whole categories (e.g. validation) |
| 2 | Selector-facing catalog metadata (`select_when`, `signals`, `pairs_with`) + candidate-aware selector prompt | Phase 1 fixes category gaps but per-page misses / overlay leaks remain |
| 3 | Recall backstop (lexical/Qdrant shortlist + graph companions) | Phases 1–2 still show misses on vocabulary-mismatch cases |
| 4 | Token-budgeted packs + Worked-Examples projection A/B | Selection recall healthy; cost or projection now the binding constraint |

---

## Phase 0: Gold Selection Set + Eval Runner

### File Structure

- Create: `evals/selection/gold_cases.json` — labeled gold cases (data, reviewed by David)
- Create: `evals/selection/README.md` — labeling rubric, so future cases stay consistent
- Create: `scripts/selection_eval.py` — runner: calls `/wiki/context-pack`, scores, writes report
- Create: `wiki_api/selection_scoring.py` — pure scoring functions (importable, unit-testable)
- Create: `tests/test_selection_scoring.py` — scoring unit tests
- Output dir (gitignored or committed per existing convention): `reports/selection-evals/`

### Gold Case Schema

Each case is a real `/wiki/context-pack` request plus three-tier labels:

```json
{
  "id": "SEL-0001",
  "source": "wiki_ask_10_tests_2026-06-19:EFSA-TD-0001",
  "reviewed": false,
  "request": {
    "search_term": "Bordsdruvor – färsk frukt (table grapes, fresh fruit)",
    "deconstructed_query": {"food": "table grapes", "state": "fresh"},
    "context": {"reporting_domain": "pesticides"},
    "candidate_hints": [],
    "max_pages": 7
  },
  "labels": {
    "must_have": [
      "base-term-selection.md",
      "pesticides-foodex2.md",
      "term-type-facet-constraints.md"
    ],
    "acceptable": [
      "facet-coding-rules.md",
      "implicit-vs-explicit-facets.md",
      "chemical-monitoring-foodex2.md",
      "foodex2-overview.md"
    ],
    "must_not": [
      "contaminants-foodex2.md",
      "vmpr-foodex2.md",
      "additives-flavourings-foodex2.md",
      "domoic-acid-scallops.md",
      "maintenance-*",
      "README.md",
      "PROJECT_CONTEXT.md"
    ],
    "notes": "Raw commodity, explicit pesticides domain. Exactly one overlay may appear."
  }
}
```

Top-level file shape: `{"version": 1, "cases": [ ... ]}`.

Conventions:

- `index.md` and `RUNTIME_RULES.md` are excluded from scoring (always present by construction).
- `must_not` entries support `fnmatch` globs (`maintenance-*`).
- `reviewed: false` marks machine-drafted labels awaiting David's sign-off; the runner has `--only-reviewed` to score the trusted subset.
- Selected pages that appear in no tier are counted as `unlabeled` and reported — they are label gaps to triage, not automatic errors.

### Labeling Rubric (goes in `evals/selection/README.md`)

Labels are derived from category policy plus case facts — you do not need to be a FoodEx2 sage to label a case:

1. **Code-construction case** (the downstream caller will build a code — true for all DMT context-pack calls): `must_have` includes `base-term-selection.md`, at least one facet page (`facet-coding-rules.md` or `implicit-vs-explicit-facets.md`), and at least one validation page (`term-type-facet-constraints.md` by default; `process-validation-rules.md` when the food is processed).
2. **Domain overlays:** the overlay page for the case's explicit domain is `must_have`; every *other* overlay page is `must_not`. If no domain signal exists, *all* overlay pages are `must_not` (all-domain default).
3. **Maintenance pages:** `must_not` (glob `maintenance-*`) unless the question is explicitly about annual changes.
4. **Orientation pages:** always `must_not` in context-pack cases.
5. **Case-fact adjustments:** packaging mentioned → `packaging-facets.md` must-have; mixed/composite food → `ingredient-facets.md` must-have; processing mentioned → `process-facets.md` must-have; and so on.
6. When unsure between `must_have` and `acceptable`, ask: *would a competent coder produce a wrong or incomplete code without this page?* Yes → must_have. No, but it is on-topic → acceptable.

### Task 1: Scoring module (TDD)

**Files:**
- Create: `wiki_api/selection_scoring.py`
- Test: `tests/test_selection_scoring.py`

**Interfaces:**
- Produces: `score_case(labels: dict, pages_used: list[str]) -> dict` returning keys `must_have_recall: float`, `precision: float`, `missing: list[str]`, `leaks: list[str]`, `unlabeled: list[str]`
- Produces: `aggregate(case_scores: list[dict]) -> dict` returning keys `mean_must_have_recall`, `mean_precision`, `leak_free_rate`, `case_count`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_selection_scoring.py
from wiki_api.selection_scoring import aggregate, score_case

LABELS = {
    "must_have": ["base-term-selection.md", "term-type-facet-constraints.md"],
    "acceptable": ["facet-coding-rules.md"],
    "must_not": ["maintenance-*", "vmpr-foodex2.md"],
}


def test_perfect_selection():
    pages = ["index.md", "RUNTIME_RULES.md", "base-term-selection.md",
             "term-type-facet-constraints.md", "facet-coding-rules.md"]
    s = score_case(LABELS, pages)
    assert s["must_have_recall"] == 1.0
    assert s["precision"] == 1.0
    assert s["missing"] == [] and s["leaks"] == [] and s["unlabeled"] == []


def test_missing_must_have_and_glob_leak():
    pages = ["index.md", "base-term-selection.md", "maintenance-2024.md"]
    s = score_case(LABELS, pages)
    assert s["must_have_recall"] == 0.5
    assert s["missing"] == ["term-type-facet-constraints.md"]
    assert s["leaks"] == ["maintenance-2024.md"]


def test_unlabeled_page_reported_not_leaked():
    pages = ["base-term-selection.md", "term-type-facet-constraints.md", "process-facets.md"]
    s = score_case(LABELS, pages)
    assert s["unlabeled"] == ["process-facets.md"]
    assert s["leaks"] == []
    assert s["precision"] == 2 / 3


def test_aggregate():
    scores = [
        {"must_have_recall": 1.0, "precision": 1.0, "leaks": []},
        {"must_have_recall": 0.5, "precision": 0.75, "leaks": ["maintenance-2024.md"]},
    ]
    agg = aggregate(scores)
    assert agg["mean_must_have_recall"] == 0.75
    assert agg["mean_precision"] == 0.875
    assert agg["leak_free_rate"] == 0.5
    assert agg["case_count"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_selection_scoring.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_api.selection_scoring'`

- [ ] **Step 3: Implement the scoring module**

```python
# wiki_api/selection_scoring.py
"""Deterministic scoring for page-selection gold cases.

Excluded from scoring: pages present by construction in every context pack.
"""
from __future__ import annotations

from fnmatch import fnmatch

ALWAYS_PRESENT = {"index.md", "RUNTIME_RULES.md"}


def _matches_any(page: str, patterns: list[str]) -> bool:
    return any(fnmatch(page, pattern) for pattern in patterns)


def score_case(labels: dict, pages_used: list[str]) -> dict:
    selected = [page for page in pages_used if page not in ALWAYS_PRESENT]
    must_have = list(labels.get("must_have", []))
    acceptable = list(labels.get("acceptable", []))
    must_not = list(labels.get("must_not", []))
    allowed = set(must_have) | set(acceptable)

    missing = [page for page in must_have if page not in selected]
    leaks = [page for page in selected if _matches_any(page, must_not)]
    unlabeled = [
        page for page in selected if page not in allowed and page not in leaks
    ]
    recall = 1.0 if not must_have else (len(must_have) - len(missing)) / len(must_have)
    precision = 1.0 if not selected else len(
        [page for page in selected if page in allowed]
    ) / len(selected)
    return {
        "must_have_recall": recall,
        "precision": precision,
        "missing": missing,
        "leaks": leaks,
        "unlabeled": unlabeled,
    }


def aggregate(case_scores: list[dict]) -> dict:
    count = len(case_scores)
    if count == 0:
        return {
            "mean_must_have_recall": 0.0,
            "mean_precision": 0.0,
            "leak_free_rate": 0.0,
            "case_count": 0,
        }
    return {
        "mean_must_have_recall": sum(s["must_have_recall"] for s in case_scores) / count,
        "mean_precision": sum(s["precision"] for s in case_scores) / count,
        "leak_free_rate": len([s for s in case_scores if not s["leaks"]]) / count,
        "case_count": count,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_selection_scoring.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add wiki_api/selection_scoring.py tests/test_selection_scoring.py
git commit -m "feat: add deterministic scoring for page-selection gold cases"
```

### Task 2: Seed gold cases from the existing ask suite

**Files:**
- Create: `evals/selection/gold_cases.json`
- Create: `evals/selection/README.md` (labeling rubric — copy the rubric section above)

**Interfaces:**
- Consumes: `/Users/davidfoster/dev/guidance_with_claude/data/wiki_ask_10_tests_2026-06-19.json` (external repo, read-only)
- Produces: `gold_cases.json` in the schema above, all cases `reviewed: false`

- [ ] **Step 1: Convert the 10 existing suite cases**

For each case in the external suite: take `food` → `request.search_term`, `reporting_domain` → `request.context.reporting_domain`, drop `reference_pages_from_run` (circular — do not copy into labels). Draft three-tier labels by applying the rubric. Use an LLM to draft, but every label must be justifiable by a rubric line; put the rubric line in `notes`.

- [ ] **Step 2: Add 5 new draft cases with candidate hints**

The existing suite has no `candidate_hints`, which is a known selector gap. Add five cases covering: (a) derivative candidates where `implicit-vs-explicit-facets.md` is must-have, (b) a VMPR biological matrix (blood/serum) case, (c) a composite/mixed food, (d) a packaging-relevant case, (e) a no-domain-signal case where *all* overlays are must_not. Invent realistic sample descriptions; mark `"source": "synthetic"`.

- [ ] **Step 3: Validate the file mechanically**

Run: `python -c "import json; d=json.load(open('evals/selection/gold_cases.json')); assert d['version']==1 and len(d['cases'])>=15; print(len(d['cases']), 'cases OK')"`
Expected: `15 cases OK` (or more)

Also verify every labeled page name (non-glob) exists as a served page:

Run: `python -c "
import json, pathlib
d = json.load(open('evals/selection/gold_cases.json'))
served = {p.name for p in pathlib.Path('raw/efsa-guidance').glob('*.md')} | {p.name for p in pathlib.Path('.').glob('*.md')}
bad = [(c['id'], page) for c in d['cases'] for tier in ('must_have', 'acceptable', 'must_not') for page in c['labels'][tier] if '*' not in page and page not in served]
print('BAD:', bad) if bad else print('all labeled pages exist')"`
Expected: `all labeled pages exist`

- [ ] **Step 4: Commit**

```bash
git add evals/selection/gold_cases.json evals/selection/README.md
git commit -m "feat: seed page-selection gold set (15 draft cases, pending review)"
```

- [ ] **Step 5: Human review checkpoint (David)**

David reviews each case against the rubric, edits labels, flips `reviewed` to `true`. This is the only step requiring domain judgment; everything else is mechanical. Budget ~30–60 minutes. Commit the reviewed file.

### Task 3: Eval runner

**Files:**
- Create: `scripts/selection_eval.py`
- Test: manual smoke run against the live API (integration; no unit test — logic lives in Task 1's tested module)

**Interfaces:**
- Consumes: `wiki_api.selection_scoring.score_case` / `aggregate`, `evals/selection/gold_cases.json`, `POST /wiki/context-pack`
- Produces: `reports/selection-evals/<YYYY-MM-DD>-<label>/results.json`

- [ ] **Step 1: Implement the runner**

```python
# scripts/selection_eval.py
"""Run the page-selection gold set against /wiki/context-pack and score it."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.selection_scoring import aggregate, score_case  # noqa: E402


def call_context_pack(base_url: str, request_payload: dict) -> dict:
    body = dict(request_payload)
    body.setdefault("include_page_content", True)
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/wiki/context-pack",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--label", required=True, help="Report label, e.g. 'baseline'.")
    parser.add_argument("--only-reviewed", action="store_true")
    args = parser.parse_args()

    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    cases = [
        case for case in gold["cases"]
        if case.get("reviewed") or not args.only_reviewed
    ]
    rows = []
    for case in cases:
        response = call_context_pack(args.base_url, case["request"])
        pages_used = response.get("pages_used", [])
        pack_chars = sum(len(page.get("content") or "") for page in response.get("pages", []))
        score = score_case(case["labels"], pages_used)
        rows.append(
            {
                "id": case["id"],
                "reviewed": bool(case.get("reviewed")),
                "pages_used": pages_used,
                "pack_chars": pack_chars,
                "selector_tokens": (response.get("trace") or {}).get("token_summary"),
                **score,
            }
        )
        print(
            f"{case['id']}: recall={score['must_have_recall']:.2f} "
            f"leaks={score['leaks']} missing={score['missing']}"
        )

    summary = aggregate(rows)
    summary["mean_pack_chars"] = (
        sum(row["pack_chars"] for row in rows) / len(rows) if rows else 0
    )
    out_dir = (
        REPO_ROOT / "reports" / "selection-evals"
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2)
    )
    print("\nSUMMARY:", json.dumps(summary, indent=2))
    print("wrote", out_dir / "results.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run against the live API**

Start the API (`uvicorn wiki_api.app:app --port 8010`), then:

Run: `python scripts/selection_eval.py --label smoke`
Expected: one line per case with recall/leaks/missing, a SUMMARY block, and `reports/selection-evals/<date>-smoke/results.json` on disk.

- [ ] **Step 3: Commit**

```bash
git add scripts/selection_eval.py
git commit -m "feat: add selection eval runner against /wiki/context-pack"
```

### Task 4: Baseline report

**Files:**
- Create: `reports/selection-evals/<date>-baseline/results.json` (runner output)
- Modify: `log.md` (one-line entry noting the baseline)

- [ ] **Step 1: Run the baseline on reviewed cases**

Run: `python scripts/selection_eval.py --label baseline --only-reviewed`
Expected: results file written; note the four headline numbers (mean must-have recall, mean precision, leak-free rate, mean pack chars).

- [ ] **Step 2: Triage the misses into phase gates**

Read per-case `missing`/`leaks`/`unlabeled`. Classify each miss: whole-category miss (→ evidence for Phase 1), vocabulary/summary miss (→ Phase 2), candidate-signal miss (→ Phase 2), genuine ambiguity (→ label fix). Record the tally in the baseline report directory as `triage.md`.

- [ ] **Step 3: Update log and commit**

```bash
git add reports/selection-evals/ log.md
git commit -m "chore: record page-selection baseline eval and triage"
```

**Phase 0 exit criteria:** ≥15 reviewed gold cases; runner produces stable deterministic scores; baseline numbers + triage recorded. The triage decides which of Phases 1–3 opens first.

---

## Phase 1 (scoped, plan later): Deterministic Category Skeleton

Encode the decision-kit skeleton as markdown-readable policy: every code-construction pack must contain ≥1 base-term page, ≥1 facet page, ≥1 validation page; domain overlay pages only when an explicit domain signal exists (and then exactly the matching one). The service enforces category quotas after selector output (fill gaps deterministically, drop leaked overlays); the LLM selector chooses only within/beyond the skeleton. Acceptance: leak-free rate and validation-page recall on the gold set improve with no precision collapse; selector token cost does not grow.

## Phase 2 (scoped, plan later): Selector-Facing Catalog + Candidate-Aware Prompt

Add `select_when` / `signals` / `pairs_with` frontmatter to prompt-facing pages; generate a machine catalog for the selector (index.md stays human-facing); doctor check: prompt-facing page without selection triggers = deterministic failure. Rewrite the selector prompt with explicit candidate-usage rules (termType → page mappings, candidate-collection → domain activation) and a completeness rubric. Acceptance: per-page misses and overlay leaks drop on gold set; candidate-hint cases (SEL synthetic set) reach full must-have recall.

## Phase 3 (scoped, plan later, evidence-gated): Recall Backstop

Only if Phases 1–2 leave vocabulary-mismatch misses: pre-compute a shortlist via `/wiki/search` lexical scoring and/or the existing Qdrant wiki collection, plus graph companions from policy/BR edges, and hand it to the selector as ranked hints with reasons. Acceptance: remaining gold-set misses close; added retrieval cost stays under an agreed token/latency budget.

## Phase 4 (scoped, plan later): Token Budgeting + Projection A/B

Replace `max_pages` with a token budget using per-page projected sizes published in the catalog; A/B the Worked-Examples projection omission against downstream coding accuracy (connects to the planned DMT eval suite). Also fold in runtime waste fixes if not already done: prompt-cache the selector system prompt + index block, and stop mutating the shared `runner.max_pages` per request ([app.py:1550](../../../wiki_api/app.py)).

---

## Self-Review Notes

- Spec coverage: gold set bootstrap (rubric + seed conversion + review checkpoint) = Tasks 1–2; measurement = Tasks 3–4; later phases scoped with gates — intentionally not task-planned yet (separate sub-projects per plan-writing scope check).
- Types consistent: `score_case`/`aggregate` signatures match between Task 1 tests, Task 1 implementation, and Task 3 runner import.
- No placeholders: all code complete; Task 2 labeling is human/LLM judgment work by design, with a mechanical validation step.
