# Expand & Re-measure Selection Eval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the selection gold set 15 → ~38 cases with a per-page coverage floor, add a miss-frequency stability metric, and re-baseline at repeats=5 to answer with data whether a systematic within-role recall ceiling exists.

**Architecture:** Pure stability metrics go in `wiki_api/selection_scoring.py` (tested); new gold cases are mined from the DMT corpus + targeted synthetic, cross-checked by an independent LLM labeling pass (`scripts/gold_crosscheck.py`) with only disagreements surfaced to David; the runner gains a miss-frequency table; a repeats=5 baseline + decision-gate triage is the deliverable. Spec: `docs/superpowers/specs/2026-07-05-expand-eval-design.md`.

**Tech Stack:** Python 3, pytest, anthropic SDK (already a dependency), existing eval conventions.

## Global Constraints

- This phase changes ONLY eval assets: `evals/`, `scripts/`, `wiki_api/selection_scoring.py`, `tests/`, `reports/`, `log.md`. NO wiki page, selector, failsafe, or prompt changes.
- The original 15 gold cases' labels are NOT modified (additions only).
- The DMT repo `/Users/davidfoster/dev/guidance_with_claude/` is READ-ONLY.
- Never change any LLM model name; the cross-check script takes `--model` and defaults to the existing `WIKI_LIBRARIAN_MODEL` env / repo default resolution — do not hardcode new names.
- Coverage floor (spec): each of `term-type-facet-constraints.md`, `validation-rules.md`, `structural-validation.md`, `business-rules.md`, `process-validation-rules.md`, `facet-coding-rules.md`, `implicit-vs-explicit-facets.md`, `process-facets.md`, `ingredient-facets.md`, `packaging-facets.md`, `code-string-format.md` must be `must_have` in ≥ 3 cases (across the full set, old + new).
- Bright line for labels: rubric-derived, situation-grounded; `must_not` overlays per domain exclusivity; `maintenance-*` + orientation pages `must_not` everywhere (unchanged rubric in `evals/selection/README.md`).
- Systematic-miss threshold (spec): a (case, page) miss is `systematic` when missed in ≥ ceil(2/3 × repeats) passes; else `stochastic`.
- phase3-baseline runs at `--repeats 5` against the current post-Phase-2 selector.

---

### Task 1: Miss-frequency stability metrics (TDD)

**Files:**
- Modify: `wiki_api/selection_scoring.py`
- Modify: `scripts/selection_eval.py`
- Test: `tests/test_selection_scoring.py`

**Interfaces:**
- Produces: `miss_frequency(pass_rows: list[list[dict]]) -> dict` in `wiki_api/selection_scoring.py`. Input: one list of case-row dicts per pass (each row has `id` and `missing`). Output:
  `{"counts": {case_id: {page: n_missed}}, "systematic": [{"case_id","page","missed","repeats"}...], "stochastic": [...]}` where `repeats = len(pass_rows)` and systematic means `missed >= math.ceil(2*repeats/3)`.
- Runner: results.json gains top-level `"miss_frequency"`; console prints the table after the median block. Existing keys unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_selection_scoring.py`:

```python
from wiki_api.selection_scoring import miss_frequency


def _row(case_id, missing):
    return {"id": case_id, "missing": missing}


def test_miss_frequency_counts_and_split():
    passes = [
        [_row("A", ["p1.md"]), _row("B", [])],
        [_row("A", ["p1.md"]), _row("B", ["p2.md"])],
        [_row("A", ["p1.md"]), _row("B", [])],
    ]
    result = miss_frequency(passes)
    assert result["counts"] == {"A": {"p1.md": 3}, "B": {"p2.md": 1}}
    assert result["systematic"] == [
        {"case_id": "A", "page": "p1.md", "missed": 3, "repeats": 3}
    ]
    assert result["stochastic"] == [
        {"case_id": "B", "page": "p2.md", "missed": 1, "repeats": 3}
    ]


def test_miss_frequency_threshold_is_ceil_two_thirds():
    # repeats=5 -> threshold ceil(10/3)=4
    passes = [
        [_row("A", ["p.md"])],
        [_row("A", ["p.md"])],
        [_row("A", ["p.md"])],
        [_row("A", [])],
        [_row("A", [])],
    ]
    assert miss_frequency(passes)["stochastic"][0]["missed"] == 3
    passes[3] = [_row("A", ["p.md"])]
    assert miss_frequency(passes)["systematic"][0]["missed"] == 4


def test_miss_frequency_empty():
    assert miss_frequency([]) == {"counts": {}, "systematic": [], "stochastic": []}
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_selection_scoring.py -k miss_frequency -v`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement**

Add to `wiki_api/selection_scoring.py`:

```python
import math


def miss_frequency(pass_rows: list[list[dict]]) -> dict:
    """Per-(case, page) miss counts across repeated eval passes.

    Separates systematic misses (>= ceil(2/3 * repeats) passes) from
    stochastic ones — the instrument that distinguishes a real selection
    gap from selector run-to-run noise.
    """
    repeats = len(pass_rows)
    counts: dict[str, dict[str, int]] = {}
    for rows in pass_rows:
        for row in rows:
            for page in row.get("missing", []):
                counts.setdefault(row["id"], {})
                counts[row["id"]][page] = counts[row["id"]].get(page, 0) + 1
    threshold = math.ceil(2 * repeats / 3) if repeats else 0
    systematic: list[dict] = []
    stochastic: list[dict] = []
    for case_id in sorted(counts):
        for page, missed in sorted(counts[case_id].items()):
            entry = {"case_id": case_id, "page": page, "missed": missed, "repeats": repeats}
            (systematic if missed >= threshold else stochastic).append(entry)
    return {"counts": counts, "systematic": systematic, "stochastic": stochastic}
```

- [ ] **Step 4: Wire into the runner**

In `scripts/selection_eval.py`: import `miss_frequency`; after the passes loop, compute `freq = miss_frequency([p["cases"] for p in passes])`; include `"miss_frequency": freq` in the results payload; after printing the median block, print:

```python
    print("\nMISS FREQUENCY (systematic = missed in >= ceil(2/3*repeats) passes):")
    for entry in freq["systematic"]:
        print(f"  SYSTEMATIC {entry['case_id']}: {entry['page']} missed {entry['missed']}/{entry['repeats']}")
    for entry in freq["stochastic"]:
        print(f"  stochastic {entry['case_id']}: {entry['page']} missed {entry['missed']}/{entry['repeats']}")
```

- [ ] **Step 5: Green + full suite + commit**

Run: `.venv/bin/python -m pytest tests/test_selection_scoring.py -v && .venv/bin/python -m pytest && python scripts/selection_eval.py --help`
Expected: all green; `--help` exit 0.

```bash
git add wiki_api/selection_scoring.py scripts/selection_eval.py tests/test_selection_scoring.py
git commit -m "feat: add miss-frequency stability metric to selection eval"
```

### Task 2: Coverage-targeted gold-set expansion (editorial)

**Files:**
- Modify: `evals/selection/gold_cases.json` (append ~23 cases, SEL-0016 onward, all `reviewed: false`)
- Modify: `evals/selection/README.md` (one short section: sourcing note for `dmt:` cases + the coverage floor)

**Interfaces:**
- Consumes: DMT corpus (READ-ONLY): `/Users/davidfoster/dev/guidance_with_claude/data/foodex2_eval_cases_from_facet_review.json` (37 cases: `id`, `query`, `must_base`, facet fields) and `foodex2_advisory_cache.json` (food descriptions). Rubric in `evals/selection/README.md`. Wiki pages under `raw/efsa-guidance/` for label grounding.
- Produces: expanded gold set meeting the coverage floor; `source` field `dmt:<file>:<case id>` or `synthetic`.

- [ ] **Step 1: Mine real cases**

Read the DMT facet-review cases; select ~12-15 diverse ones (different food types, domains, processing). Convert each: `search_term` = query (keep Swedish, add a short English gloss in parentheses as the existing cases do); `candidate_hints` from `must_base`/facet data where present (code/name/termType — verify termTypes against wiki page content, mark unverifiable ones in notes); `context.reporting_domain` only when the case clearly implies one (else omit → all-domain, all overlays must_not). Label per the rubric, reading the wiki pages the labels reference.

- [ ] **Step 2: Fill the coverage floor with targeted synthetic cases**

Count must_have coverage (old + new) per the Global Constraints page list; for every page below 3, write synthetic cases whose *situation* genuinely requires it (e.g. a malformed-code-syntax question for `structural-validation.md`; a "which BR blocks this?" construction case for `business-rules.md`; a code-assembly case for `code-string-format.md`; a multi-severity question for `validation-rules.md`). Realistic sample descriptions; `source: "synthetic"`. Aim ~8-10 synthetic; total new ≥ 23, full set ≥ 38.

- [ ] **Step 3: Mechanical validation (all must pass)**

```bash
python3 - <<'EOF'
import json, math, pathlib
from fnmatch import fnmatch
d = json.load(open('evals/selection/gold_cases.json'))
cases = d['cases']
assert len(cases) >= 38, len(cases)
ids = [c['id'] for c in cases]
assert len(ids) == len(set(ids)), 'duplicate ids'
served = {p.name for p in pathlib.Path('raw/efsa-guidance').glob('*.md')} | {p.name for p in pathlib.Path('.').glob('*.md')}
bad = [(c['id'],p) for c in cases for t in ('must_have','acceptable','must_not') for p in c['labels'][t] if '*' not in p and p not in served]
assert not bad, bad
ov = [(c['id'],p) for c in cases for t in ('must_have','acceptable') for p in c['labels'][t] if any(fnmatch(p,pat) for pat in c['labels']['must_not'])]
assert not ov, ov
FLOOR = ["term-type-facet-constraints.md","validation-rules.md","structural-validation.md","business-rules.md","process-validation-rules.md","facet-coding-rules.md","implicit-vs-explicit-facets.md","process-facets.md","ingredient-facets.md","packaging-facets.md","code-string-format.md"]
from collections import Counter
mh = Counter(p for c in cases for p in c['labels']['must_have'])
low = {p: mh.get(p,0) for p in FLOOR if mh.get(p,0) < 3}
assert not low, f'coverage floor unmet: {low}'
old = [c for c in cases if int(c['id'].split('-')[1]) <= 15]
assert all(c.get('reviewed') for c in old), 'original 15 must stay reviewed'
new = [c for c in cases if int(c['id'].split('-')[1]) > 15]
assert all(not c.get('reviewed') for c in new), 'new cases must start unreviewed'
print(f'OK: {len(cases)} cases, floor met, {len(new)} new unreviewed')
EOF
```

Expected: `OK: ...`. Also `git diff` on the file must show the original 15 cases' labels byte-identical (additions only).

- [ ] **Step 4: Doctor + suite + commit**

Run: `python -m wiki_api.doctor && .venv/bin/python -m pytest -q`

```bash
git add evals/selection/gold_cases.json evals/selection/README.md
git commit -m "feat: expand selection gold set to 38+ cases with per-page coverage floor"
```

### Task 3: Cross-check labeling script + run (produces David's disagreement report)

**Files:**
- Create: `scripts/gold_crosscheck.py`
- Output: `reports/gold-crosscheck/<date>/report.md` + `crosscheck_labels.json`

**Interfaces:**
- Consumes: gold cases with `reviewed: false`; the rubric (`evals/selection/README.md`); the served-page list.
- Produces: per-case independent labels + a diff report. Exit prints counts: agreements / disagreements.

- [ ] **Step 1: Implement the script**

`scripts/gold_crosscheck.py` (complete):

```python
"""Independent LLM cross-check of unreviewed gold-case labels.

For each case with reviewed=false, an LLM (blind to the draft labels)
produces three-tier labels from the same rubric + page list. The script
diffs them against the drafts and writes a report: agreements are
auto-acceptable; disagreements go to David.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from anthropic import Anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from wiki_api.librarian import _resolve_model  # noqa: E402
from wiki_api.wiki_store import PROMPT_CONTEXT_PAGE_CATEGORIES, WikiStore  # noqa: E402

SYSTEM = """You label FoodEx2 wiki page-selection gold cases.
Given the labeling rubric, the list of selectable wiki pages with their
descriptions, and one context-pack request, return the three-tier labels
this case SHOULD have. Work only from the rubric and page descriptions.
Return JSON only:
{"must_have": [...], "acceptable": [...], "must_not": [...], "reasoning": "..."}
Rules: page names must come from the provided list (globs like maintenance-*
allowed in must_not). Apply overlay exclusivity, maintenance/orientation
must_not, and the must_have bar: would a competent coder produce a wrong or
incomplete code without this page?"""


def label_case(client: Anthropic, model: str, rubric: str, catalog: str, case: dict) -> dict:
    prompt = json.dumps(
        {"rubric": rubric, "selectable_pages": catalog, "request": case["request"]},
        ensure_ascii=False,
    )
    response = client.messages.create(
        model=model, max_tokens=2000, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def diff_labels(draft: dict, check: dict) -> dict:
    out = {}
    for tier in ("must_have", "must_not"):
        d, c = set(draft.get(tier, [])), set(check.get(tier, []))
        if d != c:
            out[tier] = {"draft_only": sorted(d - c), "crosscheck_only": sorted(c - d)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--model", default=None, help="Override; defaults to repo librarian model resolution.")
    args = parser.parse_args()

    model = args.model or _resolve_model("WIKI_LIBRARIAN_MODEL", default="claude-sonnet-4-6")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    store = WikiStore(str(REPO_ROOT))
    rubric = (REPO_ROOT / "evals/selection/README.md").read_text()
    catalog = "\n".join(
        f"- {n}: {store.read_page(n).select_when or store.read_page(n).summary}"
        for n in store.list_pages()
    )
    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    targets = [c for c in gold["cases"] if not c.get("reviewed")]

    out_dir = REPO_ROOT / "reports" / "gold-crosscheck" / dt.date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    all_checks, agreements, disagreements = {}, [], []
    for case in targets:
        check = label_case(client, model, rubric, catalog, case)
        all_checks[case["id"]] = check
        delta = diff_labels(case["labels"], check)
        if delta:
            disagreements.append((case["id"], delta, check.get("reasoning", "")))
        else:
            agreements.append(case["id"])
        print(f"{case['id']}: {'AGREE' if not delta else 'DISAGREE ' + json.dumps(delta, ensure_ascii=False)}")

    (out_dir / "crosscheck_labels.json").write_text(json.dumps(all_checks, ensure_ascii=False, indent=2))
    lines = [f"# Gold cross-check {dt.date.today().isoformat()} (model: {model})", "",
             f"Agreements ({len(agreements)}): {', '.join(agreements)}", "", "## Disagreements — David to resolve", ""]
    for cid, delta, why in disagreements:
        lines += [f"### {cid}", f"- delta: `{json.dumps(delta, ensure_ascii=False)}`", f"- cross-check reasoning: {why}", ""]
    (out_dir / "report.md").write_text("\n".join(lines))
    print(f"\n{len(agreements)} agree / {len(disagreements)} disagree -> {out_dir}/report.md")


if __name__ == "__main__":
    main()
```

Note: `_resolve_model` is private to `wiki_api.librarian` — acceptable for an ops script in this repo (matches existing script conventions); if its import fails, fall back to `os.getenv("WIKI_LIBRARIAN_MODEL", "claude-sonnet-4-6")`.

- [ ] **Step 2: Run it**

Run: `.venv/bin/python scripts/gold_crosscheck.py`
Expected: one AGREE/DISAGREE line per unreviewed case; report under `reports/gold-crosscheck/<date>/`. (~23 LLM calls.)

- [ ] **Step 3: Commit script + report**

```bash
git add scripts/gold_crosscheck.py reports/gold-crosscheck/
git commit -m "feat: add independent LLM cross-check for gold-case labels"
```

- [ ] **Step 4: HUMAN CHECKPOINT — David resolves disagreements**

Present the disagreement list to David (summarized, with the cross-check reasoning). For each: keep draft, take cross-check, or edit. Apply his resolutions to `gold_cases.json`.

### Task 4: Flip reviewed + re-validate

**Files:**
- Modify: `evals/selection/gold_cases.json`

- [ ] **Step 1:** After resolutions applied: set `reviewed: true` on all new cases (agreements auto-accepted per design; disagreements now David-resolved).
- [ ] **Step 2:** Re-run the Task 2 Step 3 mechanical validation (adjust the reviewed assertions: now ALL cases reviewed). Expected: OK.
- [ ] **Step 3:** `.venv/bin/python -m pytest -q && python -m wiki_api.doctor` → green/clean.
- [ ] **Step 4:**

```bash
git add evals/selection/gold_cases.json
git commit -m "chore: finalize expanded gold set after cross-check review"
```

### Task 5: phase3-baseline (repeats=5) + decision-gate triage

**Files:**
- Output: `reports/selection-evals/<date>-phase3-baseline/{results.json,triage.md}`
- Modify: `log.md`

- [ ] **Step 1: Run the baseline**

API must run current main+branch code (start own instance: `.venv/bin/python -m uvicorn wiki_api.app:app --port 8014`, probe `trace.skeleton_enforcement`, stop it after). Then:

Run: `python scripts/selection_eval.py --label phase3-baseline --only-reviewed --repeats 5 [--base-url http://127.0.0.1:8014]`
Expected: 5 passes × ≥38 cases (~190+ selector calls; this is the big run), median block + miss-frequency table.

- [ ] **Step 2: Write the decision-gate triage**

`triage.md` must contain: metric medians (recall/precision/leak-free/backfill/tokens) with min-max; the full miss-frequency table; **the gate answer** — systematic within-role ceiling YES (list exactly which (case, page) pairs are systematic, which pages recur, and a recommendation for a follow-up mechanism phase measured against this set) or NO (state plainly that recall is solved and the Phase 2 "ceiling" was noise; recommend no mechanism). Include honest caveats (e.g. new-case label quality, backfill-rate comparability — the expanded set changes the denominator, so do NOT compare rates to phase2 directly; note this).

- [ ] **Step 3: log.md entry**

New dated `diagnostic` entry: gold set expanded to N with coverage floor, cross-check stats (X agree / Y disagree, resolved), miss-frequency instrument added, phase3-baseline medians, and the gate verdict in one sentence.

- [ ] **Step 4: Final green + commit**

Run: `.venv/bin/python -m pytest -q && python -m wiki_api.doctor`

```bash
git add reports/selection-evals/ log.md
git commit -m "feat: phase3 baseline on expanded gold set with systematic-miss gate verdict"
```

---

## Self-Review Notes

- Spec coverage: metric (Task 1), expansion + floor (Task 2), cross-check + David's disagreement-only review (Task 3 + checkpoint), finalize (Task 4), repeats=5 baseline + gate (Task 5). No mechanism task — correct, it's out of scope by design.
- Type consistency: `miss_frequency(pass_rows) -> {"counts","systematic","stochastic"}` matches between Task 1 tests/impl/runner wiring and Task 5's triage table.
- Checkpoint honesty: Task 3 Step 4 is a hard stop for David; Tasks 4-5 depend on it.
- Placeholders: none; all code complete; editorial Task 2 has mechanical acceptance.
