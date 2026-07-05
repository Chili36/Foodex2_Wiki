# Candidate-Aware Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the LLM page selector candidate-aware and give every prompt-facing page a `select_when` hint, driving the Phase 1 backfill rate from 0.93 toward ≤ 0.33 without touching the failsafe.

**Architecture:** A `select_when` frontmatter field feeds a generated selector catalog (fallback: index summaries) that replaces `index.md` as selector input; a Selector Guidance prose section in `selection-policy.md` is injected into the selector system prompt; doctor + lint + the gold-set eval keep the LLM-written metadata honest. Spec: `docs/superpowers/specs/2026-07-05-candidate-aware-selector-design.md`.

**Tech Stack:** Python 3, FastAPI, PyYAML, pytest; existing eval conventions in `scripts/` + `reports/`.

## Global Constraints

- Never change any LLM model name.
- The Phase 1 failsafe (`enforce_skeleton`, policy YAML block, drop rules) is NOT modified.
- `evals/selection/gold_cases.json` labels are NOT modified (ground truth does not move while tuning).
- Bright line, including metadata phrasing: `select_when` and Selector Guidance describe situations/concepts and term-type *meanings* — never query-keyword→page or termType→filename mappings.
- `select_when` writing rules: situation vocabulary, complete sentences, ≤ ~60 words (doctor bound: ≤ 400 chars). Only prompt-facing pages (categories runtime/guidance/validation/domain_overlay) get the field.
- Token economy: selector token cost median must stay ≤ 1.5 × the phase1-r3 reference median.
- `index.md` stays human-facing and unchanged in role; EFSA's FoodEx2 term catalogue is untouched (different thing entirely).
- Acceptance is measured as median of 3 eval runs (`--repeats 3`).

---

### Task 0: `--repeats` in the eval runner + phase1-r3 reference run

**Files:**
- Modify: `scripts/selection_eval.py`
- Output: `reports/selection-evals/<date>-phase1-r3/results.json`

**Interfaces:**
- Produces: CLI flag `--repeats N` (default 1); results.json shape `{"repeats": N, "passes": [{"summary": {...}, "cases": [...]}, ...], "median_summary": {...}}`; each pass summary gains `mean_selector_tokens`; `median_summary` holds median/min/max per numeric metric. Task 6 consumes `median_summary` and per-pass `cases[].backfilled`.

- [ ] **Step 1: Refactor the case loop into `run_pass` and add repeats**

Restructure `main()` in `scripts/selection_eval.py`. Preserve the existing load-time gold invariant check, the `pages_used` malformed-response RuntimeError, and the `skeleton_enforcement` missing-trace RuntimeError exactly as they are — move them, do not rewrite them. Target shape:

```python
def run_pass(cases: list[dict], base_url: str, pass_number: int) -> tuple[list[dict], dict]:
    rows = []
    for case in cases:
        response = call_context_pack(base_url, case["request"])
        pages_used = response.get("pages_used")
        if not isinstance(pages_used, list):
            raise RuntimeError(
                f"{case['id']}: malformed /wiki/context-pack response: missing pages_used"
            )
        trace = response.get("trace") or {}
        if "skeleton_enforcement" not in trace:
            raise RuntimeError(
                f"{case['id']}: response trace lacks skeleton_enforcement — "
                "is the server running pre-enforcement code?"
            )
        enforcement = trace["skeleton_enforcement"]
        pack_chars = sum(len(page.get("content") or "") for page in response.get("pages", []))
        score = score_case(case["labels"], pages_used)
        row = {
            "id": case["id"],
            "reviewed": bool(case.get("reviewed")),
            "pages_used": pages_used,
            "pack_chars": pack_chars,
            "selector_tokens": trace.get("token_summary"),
            "backfilled": enforcement.get("backfilled", []),
            "dropped": enforcement.get("dropped", []),
            **score,
        }
        rows.append(row)
        print(
            f"[pass {pass_number}] {case['id']}: recall={score['must_have_recall']:.2f} "
            f"leaks={score['leaks']} missing={score['missing']} "
            f"backfilled={[item['page'] for item in row['backfilled']]}"
        )
    summary = aggregate(rows)
    summary["mean_pack_chars"] = sum(r["pack_chars"] for r in rows) / len(rows) if rows else 0
    summary["backfill_case_rate"] = (
        len([r for r in rows if r["backfilled"]]) / len(rows) if rows else 0
    )
    summary["mean_backfills_per_case"] = (
        sum(len(r["backfilled"]) for r in rows) / len(rows) if rows else 0
    )
    token_totals = [
        (r["selector_tokens"] or {}).get("total_tracked_tokens")
        for r in rows
        if isinstance(r.get("selector_tokens"), dict)
    ]
    token_totals = [t for t in token_totals if isinstance(t, (int, float))]
    summary["mean_selector_tokens"] = (
        sum(token_totals) / len(token_totals) if token_totals else 0
    )
    return rows, summary
```

(If the current loop body differs in detail from the sketch above, the current file governs — this is a refactor, not a rewrite.)

In `main()`: add `parser.add_argument("--repeats", type=int, default=1)`; loop `for pass_number in range(1, args.repeats + 1)`, collect `passes = [{"summary": s, "cases": rows}, ...]`; compute:

```python
import statistics

MEDIAN_METRICS = [
    "mean_must_have_recall", "mean_precision", "leak_free_rate",
    "mean_pack_chars", "backfill_case_rate", "mean_backfills_per_case",
    "mean_selector_tokens",
]

def median_summary(passes: list[dict]) -> dict:
    out = {}
    for metric in MEDIAN_METRICS:
        values = [p["summary"][metric] for p in passes]
        out[metric] = {
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    out["passes"] = len(passes)
    return out
```

Write `{"repeats": args.repeats, "passes": passes, "median_summary": median_summary(passes)}` to the results file; print each pass summary and the median block.

- [ ] **Step 2: Sanity-check the flag offline**

Run: `python scripts/selection_eval.py --help`
Expected: exit 0, `--repeats` listed.

- [ ] **Step 3: Run the phase1-r3 reference against the live API**

Start the API if needed (`uvicorn wiki_api.app:app --port 8011` from repo root; `.env` supplies keys; verify `trace.skeleton_enforcement` exists in a probe response before trusting any instance; do not kill processes you did not start). Then:

Run: `python scripts/selection_eval.py --label phase1-r3 --only-reviewed --repeats 3 [--base-url http://127.0.0.1:8011]`
Expected: 3 passes × 15 cases; median block printed; `reports/selection-evals/<date>-phase1-r3/results.json` written. Expect medians near: recall ~0.97, backfill_case_rate ~0.93, mean_selector_tokens ~3600. Record these — they are the Phase 2 reference.

- [ ] **Step 4: Full suite + commit**

Run: `python -m pytest` (green) then:

```bash
git add scripts/selection_eval.py reports/selection-evals/
git commit -m "feat: add eval repeats and record phase1-r3 reference medians"
```

### Task 1: `select_when` field + generated selector catalog (TDD)

**Files:**
- Modify: `wiki_api/wiki_store.py`
- Test: `tests/test_wiki_store_catalog.py` (new)

**Interfaces:**
- Produces: `WikiPage.select_when: str | None` (new dataclass field, default `None`); `WikiStore.selector_catalog() -> str` returning one line per prompt-facing page: `- <name> — <select_when or index summary>`. Task 3 consumes `selector_catalog()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_wiki_store_catalog.py`:

```python
from wiki_api.wiki_store import WikiStore


def test_read_page_parses_select_when(tmp_path):
    store = _make_store(tmp_path)
    page = store.read_page("annotated.md")
    assert page.select_when == "The case involves choosing between raw and derivative bases."


def test_read_page_select_when_absent_is_none(tmp_path):
    store = _make_store(tmp_path)
    assert store.read_page("plain.md").select_when is None


def test_selector_catalog_prefers_select_when_and_falls_back_to_summary(tmp_path):
    store = _make_store(tmp_path)
    catalog = store.selector_catalog()
    assert "- annotated.md — The case involves choosing between raw and derivative bases." in catalog
    assert "- plain.md — Summary line for plain page." in catalog


def test_selector_catalog_excludes_non_prompt_facing_pages(tmp_path):
    store = _make_store(tmp_path)
    catalog = store.selector_catalog()
    assert "README.md" not in catalog
    assert "maintenance-2024.md" not in catalog


def _make_store(tmp_path):
    root = tmp_path
    guidance = root / "raw" / "efsa-guidance"
    guidance.mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md",
                 "WIKI_ARCHITECTURE_FOR_MODELS.md", "INGEST_WORKFLOW.md",
                 "MAINTENANCE_WORKFLOW.md", "SCHEMA.md", "RUNTIME_RULES.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    (guidance / "annotated.md").write_text(
        "---\ntitle: Annotated\nselect_when: >-\n  The case involves choosing between "
        "raw and derivative bases.\n---\n# Annotated\n"
    )
    (guidance / "plain.md").write_text("---\ntitle: Plain\n---\n# Plain\n")
    (guidance / "maintenance-2024.md").write_text("---\ntitle: M24\n---\n# M24\n")
    (root / "index.md").write_text(
        "---\ntitle: Index\n---\n# Index\n\n## Guidance\n\n"
        "- [annotated.md](raw/efsa-guidance/annotated.md): Summary for annotated page.\n"
        "- [plain.md](raw/efsa-guidance/plain.md): Summary line for plain page.\n"
        "- [maintenance-2024.md](raw/efsa-guidance/maintenance-2024.md): M24 summary.\n"
    )
    return WikiStore(root)
```

Adaptation note: in the temp store, `page_category` returns `"guidance"` for any file in the guidance dir not in the category map — that is what makes `annotated.md`/`plain.md` prompt-facing here. `maintenance-2024.md` IS in the real category map as `maintenance`, which is why the exclusion test uses that exact name. If the category map lookup happens before the guidance-dir fallback (check `page_category`), this works as written; verify before assuming.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_wiki_store_catalog.py -v`
Expected: FAIL — `WikiPage` has no `select_when`; `WikiStore` has no `selector_catalog`.

- [ ] **Step 3: Implement**

In `wiki_api/wiki_store.py`:

Add to `WikiPage` (after `body: str`):

```python
    select_when: str | None = None
```

In `read_page`, after the `related` extraction, add:

```python
        select_when_raw = frontmatter.get("select_when")
        select_when = (
            " ".join(str(select_when_raw).split()) if isinstance(select_when_raw, str) and select_when_raw.strip() else None
        )
```

and pass `select_when=select_when` to the `WikiPage(...)` constructor.

Add the method (near `catalog()`):

```python
    def selector_catalog(self) -> str:
        """Selector-facing page catalog: one line per prompt-facing page.

        Prefers the page's select_when hint; falls back to its index.md
        summary so unannotated pages stay selectable (never invisible).
        """
        lines: list[str] = []
        for name in self.list_pages():
            if self.page_category(name) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
                continue
            page = self.read_page(name)
            description = page.select_when or page.summary or page.title
            lines.append(f"- {name} — {description}")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests, then full suite**

Run: `python -m pytest tests/test_wiki_store_catalog.py -v && python -m pytest`
Expected: new tests pass; full suite green (the added dataclass field has a default, so existing constructions are unaffected).

- [ ] **Step 5: Commit**

```bash
git add wiki_api/wiki_store.py tests/test_wiki_store_catalog.py
git commit -m "feat: add select_when field and generated selector catalog"
```

### Task 2: Selector Guidance section + loader (TDD)

**Files:**
- Modify: `raw/efsa-guidance/selection-policy.md`
- Modify: `wiki_api/selection_policy.py`
- Modify: `wiki_api/doctor.py` (extend `_check_selection_policy`)
- Test: `tests/test_selection_policy.py`, `tests/test_wiki_doctor.py`

**Interfaces:**
- Produces: `load_selector_guidance(store: WikiStore) -> str` in `wiki_api/selection_policy.py` (raises `ValueError` if the section is missing/empty); a `## Selector Guidance` section in `selection-policy.md`. Task 3 consumes the loader.

- [ ] **Step 1: Add the Selector Guidance section to the policy page**

Append to `raw/efsa-guidance/selection-policy.md` (after the Policy Block section), exactly:

```markdown
## Selector Guidance

This section is loaded by the wiki service and injected into the page
selector's system prompt. It teaches the selector how to read a coding
case. It describes meanings and situations only — it must never map query
keywords or term types to page filenames.

### Reading The Candidate List

- Candidate `termType` values follow the FoodEx2 term-type model:
  `r` raw commodity, `d` derivative, `c` composite, `s` simple composite,
  `h` hierarchy, `g` generic or group, `f` facet descriptor, and
  `n` non-specific.
- A candidate set that mixes raw and derivative terms for the same
  commodity means the coder must decide which descriptive details are
  already implicit in a derivative base and which need explicit facets.
  Prefer pages whose selection hints cover implicit-versus-explicit
  reasoning and raw-versus-derivative process boundaries.
- Hierarchy, group, facet, or non-specific terms in the candidate list are
  traps: they are discouraged or invalid as reportable base terms, and the
  coder must be steered toward a legal specific term. When such candidates
  appear, prefer pages whose hints cover base-term legality and term-type
  constraints.

### Reading The Context

- An explicit reporting domain in the case context activates exactly that
  domain's overlay thinking. Never select overlay pages for domains the
  case does not signal; with no domain signal, the all-domain default
  applies and no overlay page belongs in the pack.
- Processing, packaging, ingredient, mixture, or physical-state details in
  the query or deconstructed query are real coding work. Prefer pages
  whose hints cover those facet families and the validation rules that
  constrain them.

### Completeness Rubric

A FoodEx2 code will be constructed from the pack you assemble. The pack
must let the coder resolve the food type, the best reportable base term,
which facets are legal and needed, and how the construction will be
validated. Ask what this specific case makes difficult, then choose the
pages whose selection hints address those difficulties. Do not pad the
pack with pages the case does not need.
```

Also update the page's intro sentence ("This page defines the deterministic failsafe...") to mention it now also carries the selector guidance, and bump `last_updated` to the current date.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_selection_policy.py`:

```python
from wiki_api.selection_policy import load_selector_guidance


def test_load_selector_guidance_from_wiki():
    store = WikiStore(".")
    guidance = load_selector_guidance(store)
    assert "Reading The Candidate List" in guidance
    assert "Completeness Rubric" in guidance
    assert "```" not in guidance  # prose only, no fenced blocks


def test_load_selector_guidance_missing_section_raises(tmp_path):
    # reuse the minimal temp-root scaffolding from
    # test_load_selection_policy_rejects_missing_block, but write a
    # selection-policy.md WITH a valid yaml block and WITHOUT a
    # "## Selector Guidance" section
    ...
```

Write the second test fully by copying the existing temp-root helper pattern in this file; assert `pytest.raises(ValueError, match="Selector Guidance")`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_selection_policy.py -k guidance -v`
Expected: FAIL with ImportError (`load_selector_guidance` does not exist).

- [ ] **Step 4: Implement the loader**

In `wiki_api/selection_policy.py`:

```python
_GUIDANCE_HEADER = "## Selector Guidance"


def load_selector_guidance(store: WikiStore) -> str:
    """Extract the Selector Guidance prose from the policy page.

    Re-read per call, matching the module's no-caching idiom.
    """
    try:
        page = store.read_page(POLICY_PAGE_NAME)
    except (FileNotFoundError, OSError) as exc:
        raise ValueError(f"{POLICY_PAGE_NAME} could not be read: {exc}") from exc
    lines = page.content.splitlines()
    collected: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == _GUIDANCE_HEADER:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            collected.append(line)
    guidance = "\n".join(collected).strip()
    if not guidance:
        raise ValueError(f"{POLICY_PAGE_NAME} has no Selector Guidance section")
    return guidance
```

- [ ] **Step 5: Extend the doctor check**

In `wiki_api/doctor.py` `_check_selection_policy`, after the existing drop-pages loop, add:

```python
    try:
        load_selector_guidance(store)
    except ValueError as exc:
        issues.append(
            DoctorIssue(
                severity="error",
                check="selection_policy",
                location=POLICY_PAGE_NAME,
                message=f"selector guidance unavailable: {exc}",
            )
        )
```

(Import `load_selector_guidance` alongside the existing imports.) Add a doctor test in `tests/test_wiki_doctor.py` mirroring the corrupted-policy test: valid YAML block, guidance section removed → `selection_policy` error present.

- [ ] **Step 6: Run tests, doctor, full suite; commit**

Run: `python -m pytest -q && python -m wiki_api.doctor`
Expected: green; doctor clean on the real wiki.

```bash
git add raw/efsa-guidance/selection-policy.md wiki_api/selection_policy.py wiki_api/doctor.py tests/test_selection_policy.py tests/test_wiki_doctor.py
git commit -m "feat: add selector guidance section, loader, and doctor coverage"
```

### Task 3: Wire selector to catalog + guidance (TDD)

**Files:**
- Modify: `wiki_api/librarian.py` (`build_selection_system_prompt`, `AnthropicWikiPageSelector.run`, `JsonWikiPageSelector.run`)
- Test: `tests/test_librarian.py`

**Interfaces:**
- Consumes: `WikiStore.selector_catalog()` (Task 1), `load_selector_guidance` (Task 2).
- Produces: `build_selection_system_prompt(*, additional_page_limit: int, selector_guidance: str) -> str`; both selector classes send `{"case": payload, "selector_catalog": <catalog>}` as the user message (replacing `wiki_index`).

- [ ] **Step 1: Study the existing test idiom, then write failing tests**

Read `tests/test_librarian.py` to find how selector classes are tested (stub client capturing `messages.create` kwargs). Add tests asserting, for BOTH `AnthropicWikiPageSelector` and `JsonWikiPageSelector` (the latter via its logged/prepared user content if it cannot take a stub client — check `_create_json_completion` usage; if unstubable without HTTP, test `AnthropicWikiPageSelector` fully and cover `JsonWikiPageSelector` by extracting a shared helper that builds the user message and asserting on the helper):

```python
def test_selector_prompt_carries_guidance_and_catalog(...):
    # system prompt contains "Reading The Candidate List" (guidance injected)
    # user message JSON has key "selector_catalog" whose value contains "- base-term-selection.md — "
    # user message JSON has no "wiki_index" key
```

Shared-helper approach (preferred, keeps the two classes in sync):

```python
def build_selection_user_content(*, store: WikiStore, payload: dict[str, Any]) -> str:
    return json.dumps(
        {"case": payload, "selector_catalog": store.selector_catalog()},
        ensure_ascii=False,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_librarian.py -k "guidance or catalog" -v`
Expected: FAIL (prompt builder lacks the parameter; user message still uses `wiki_index`).

- [ ] **Step 3: Implement**

In `wiki_api/librarian.py`:

Change the prompt builder to accept and embed the guidance:

```python
def build_selection_system_prompt(*, additional_page_limit: int, selector_guidance: str) -> str:
    return f"""You are the FoodEx2 wiki page selector.

Your only job is to choose which wiki pages should be returned as context for the current coding case so another model can create the correct FoodEx2 code.

How to read the case:

{selector_guidance}

Rules:
- The selector catalog of available wiki pages is provided in the user message; each entry describes the situations in which that page should be selected.
- Use the query, deconstructed query, candidate list, catalog, and the guidance above together.
- Return only the pages needed for this case.
- Do not solve the FoodEx2 coding task.
- Do not summarize or rewrite the wiki.
- Request at most {additional_page_limit} additional wiki pages.
- If no additional pages are needed, return JSON only: {{"page_names": []}}
"""
```

Add `from .selection_policy import load_selector_guidance` and the shared `build_selection_user_content` helper. In both `AnthropicWikiPageSelector.run` and `JsonWikiPageSelector.run`: replace `index_content = self.store.read_page("index.md").content` and the `{"case": payload, "wiki_index": index_content}` user message with `load_selector_guidance(self.store)` + `build_selection_user_content(store=self.store, payload=payload)`, and pass `selector_guidance=` into `build_selection_system_prompt`.

Do not modify `AnthropicWikiLibrarian` (policy-pack) — out of scope.

- [ ] **Step 4: Run tests, full suite; commit**

Run: `python -m pytest tests/test_librarian.py -v && python -m pytest`
Expected: green (existing librarian tests may need their captured-prompt assertions updated from `wiki_index` to `selector_catalog` — update assertions to the new contract, do not weaken them).

```bash
git add wiki_api/librarian.py tests/test_librarian.py
git commit -m "feat: selector reads generated catalog and markdown guidance"
```

### Task 4: Annotate all prompt-facing pages with `select_when`

**Files:**
- Modify: every prompt-facing page under `raw/efsa-guidance/` plus `RUNTIME_RULES.md` and `policy-contract.md` (categories runtime/guidance/validation/domain_overlay — enumerate live via the category map in `wiki_api/wiki_store.py:113`; ~25 pages)

**Interfaces:**
- Consumes: writing rules from the spec (situation vocabulary, ≤ ~60 words, ≤ 400 chars, complete sentences; NO query-keyword/filename/termType→page phrasing).
- Produces: `select_when` frontmatter on every prompt-facing page; Task 5's doctor check will enforce this set.

- [ ] **Step 1: Enumerate the target pages**

Run: `python -c "from wiki_api.wiki_store import WikiStore, PROMPT_CONTEXT_PAGE_CATEGORIES; s=WikiStore('.'); print('\n'.join(n for n in s.list_pages() if s.page_category(n) in PROMPT_CONTEXT_PAGE_CATEGORIES))"`
Expected: ~25 page names. This list is the annotation scope — no more, no less.

- [ ] **Step 2: Write the annotations**

For each page: read the page fully, then write a `select_when` that answers "in what coding situations does this page change the outcome?" from the page's actual content. Style examples:

Good (situation vocabulary, from content):
```yaml
select_when: >-
  The case requires deciding whether a candidate term is legal as a
  reportable base term, or which facet categories a chosen term type
  permits or forbids — including when hierarchy, group, or facet terms
  appear among the candidates.
```

Forbidden (bright-line violations — never write these):
```yaml
select_when: "Select when the query mentions scallops"          # query keyword
select_when: "If termType is d, select implicit-vs-explicit"    # termType→page rule
```

Sibling pages must be distinguishable: the hints for `validation-rules.md`, `structural-validation.md`, `business-rules.md`, `term-type-facet-constraints.md`, and `process-validation-rules.md` must each name what that page uniquely resolves, not generic "validation matters."

- [ ] **Step 3: Mechanical validation**

Run: `python -c "
from wiki_api.wiki_store import WikiStore, PROMPT_CONTEXT_PAGE_CATEGORIES
s = WikiStore('.')
bad = []
for n in s.list_pages():
    if s.page_category(n) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
        continue
    p = s.read_page(n)
    if not p.select_when:
        bad.append((n, 'missing'))
    elif len(p.select_when) > 400:
        bad.append((n, f'too long: {len(p.select_when)}'))
print('BAD:', bad) if bad else print('all prompt-facing pages annotated')"`
Expected: `all prompt-facing pages annotated`

Also render the catalog and eyeball total size: `python -c "from wiki_api.wiki_store import WikiStore; c=WikiStore('.').selector_catalog(); print(c); print('chars:', len(c))"` — expect roughly 4,000–8,000 chars (~1,000–2,000 tokens).

- [ ] **Step 4: Doctor + full suite + commit**

Run: `python -m wiki_api.doctor && python -m pytest -q`
Expected: clean/green (the select_when doctor check does not exist yet — that is Task 5; this run just proves no regressions).

```bash
git add raw/efsa-guidance/ RUNTIME_RULES.md
git commit -m "feat: annotate prompt-facing pages with select_when selection hints"
```

### Task 5: Doctor `selection_metadata` check + SCHEMA/INGEST docs (TDD)

**Files:**
- Modify: `wiki_api/doctor.py`
- Modify: `SCHEMA.md`, `INGEST_WORKFLOW.md`
- Test: `tests/test_wiki_doctor.py`

**Interfaces:**
- Consumes: `WikiPage.select_when`, `PROMPT_CONTEXT_PAGE_CATEGORIES`.
- Produces: doctor check name `selection_metadata`.

- [ ] **Step 1: Write the failing test**

In `tests/test_wiki_doctor.py`, using the existing `_copy_wiki_root` helper: copy the wiki, strip `select_when` from one prompt-facing page's frontmatter (e.g. rewrite `base-term-selection.md` frontmatter without the field), run the doctor, assert an error with `check == "selection_metadata"` naming that page. Second test: real wiki has no `selection_metadata` errors.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_wiki_doctor.py -k selection_metadata -v`
Expected: first test FAILS (check doesn't exist).

- [ ] **Step 3: Implement the check**

In `wiki_api/doctor.py`, new function wired into `run_doctor` after `_check_selection_policy`:

```python
SELECT_WHEN_MAX_CHARS = 400


def _check_selection_metadata(store: WikiStore) -> Iterable[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for name in store.list_pages():
        if store.page_category(name) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
            continue
        page = store.read_page(name)
        if not page.select_when:
            issues.append(
                DoctorIssue(
                    severity="error",
                    check="selection_metadata",
                    location=name,
                    message="prompt-facing page has no select_when frontmatter",
                )
            )
        elif len(page.select_when) > SELECT_WHEN_MAX_CHARS:
            issues.append(
                DoctorIssue(
                    severity="error",
                    check="selection_metadata",
                    location=name,
                    message=f"select_when exceeds {SELECT_WHEN_MAX_CHARS} chars ({len(page.select_when)})",
                )
            )
    return issues
```

- [ ] **Step 4: Update the docs**

`SCHEMA.md`: add `select_when` to the frontmatter-fields section — definition, the writing rules (situation vocabulary, ≤ ~60 words / 400 chars, complete sentences), the good and forbidden examples from Task 4 Step 2, and the note that only prompt-facing pages carry it and the doctor enforces it.

`INGEST_WORKFLOW.md`: in the topic-page authoring/patch step, add: "Every created or materially changed prompt-facing page gets a `select_when` hint written or refreshed against the writing rules in `SCHEMA.md`. The doctor fails pages that lack it. Optionally run `python -m wiki_api.llm_lint --page <page> --focus 'select_when hint quality: situation phrasing, no query-keyword or term-type-to-page mappings, accurate to page content'` for a supervised quality pass."

- [ ] **Step 5: Run tests, doctor, full suite; commit**

Run: `python -m pytest -q && python -m wiki_api.doctor`
Expected: green; doctor clean (all pages were annotated in Task 4).

```bash
git add wiki_api/doctor.py tests/test_wiki_doctor.py SCHEMA.md INGEST_WORKFLOW.md
git commit -m "feat: doctor enforces select_when on prompt-facing pages; document in schema and ingest workflow"
```

### Task 6: Lint pass, phase2 eval (3 repeats), acceptance, iteration cap

**Files:**
- Output: `reports/selection-evals/<date>-phase2-r3/results.json` + `triage.md`
- Modify: `log.md`; possibly `raw/efsa-guidance/*` `select_when` wording and/or the Selector Guidance section (revision rounds only)

**Interfaces:**
- Consumes: Task 0's `median_summary` + phase1-r3 reference; acceptance criteria from the spec.

- [ ] **Step 1: Lint the annotations (supervised aid, findings triaged not auto-fixed)**

For each of the 5 validation-layer pages plus 3 spot-check guidance pages, run:
`python -m wiki_api.llm_lint --page <page> --focus "select_when hint: situation phrasing only, no query-keyword or termType-to-page mappings, accurate to this page's content, distinguishable from sibling pages"`
Record findings in the triage; fix clear bright-line violations before the eval run.

- [ ] **Step 2: Run the phase2 eval**

API instance must be running the NEW code (probe: selector trace present AND a context-pack response whose selector prompt path uses the catalog — restart your own instance to be sure).

Run: `python scripts/selection_eval.py --label phase2-r3 --only-reviewed --repeats 3 [--base-url ...]`

- [ ] **Step 3: Score against acceptance (medians vs phase1-r3 reference)**

1. `backfill_case_rate` median ≤ 0.33
2. SEL-0005 selects `process-validation-rules.md` and SEL-0011 selects `implicit-vs-explicit-facets.md` via the selector (not backfill) in ≥ 2 of 3 passes
3. recall / precision / leak-free medians ≥ phase1-r3 medians
4. `mean_selector_tokens` median ≤ 1.5 × phase1-r3 median
5. doctor clean, full suite green

- [ ] **Step 4: Iteration cap (only if the bar is missed)**

At most TWO revision rounds. Each round: read the failing cases' per-pass `pages_used` + `backfilled`, diagnose (hint wording? guidance gap? sibling-page blur?), revise ONLY `select_when` wording and/or Selector Guidance prose, re-run Step 2 with a new label (`phase2-r3-rev1`, `-rev2`). If still short after round 2: STOP. Write the structural findings into the triage (this becomes Phase 3 evidence) and report honestly — do not tune further.

- [ ] **Step 5: Triage + log + commit**

`reports/selection-evals/<date>-phase2-r3/triage.md`: metric table (phase1-r3 vs phase2-r3 medians with min/max), acceptance verdict per criterion, per-case notes for SEL-0005/SEL-0011, lint findings summary, revision rounds used (if any) and what each changed, honest caveats.

`log.md`: new dated `maintenance` entry — selector catalog + guidance live, annotation coverage, doctor check, phase2 numbers vs phase1-r3, backfill rate as the ongoing scoreboard.

Run: `python -m pytest -q && python -m wiki_api.doctor` then:

```bash
git add reports/selection-evals/ log.md raw/efsa-guidance/ index.md
git commit -m "feat: record phase2 candidate-aware selector eval vs phase1-r3 reference"
```

---

## Self-Review Notes

- Spec coverage: Task 0 (repeats + reference), Task 1 (field + catalog + fallback), Task 2 (guidance + loader + doctor), Task 3 (selector wiring, both classes, shared helper), Task 4 (full annotation scope), Task 5 (doctor enforcement + SCHEMA/INGEST), Task 6 (lint + eval + acceptance + iteration cap). Out-of-scope list has no tasks, as intended.
- Ordering: annotation (Task 4) precedes doctor enforcement (Task 5) so the branch never has a failing doctor; catalog fallback (Task 1) means Tasks 1–3 work pre-annotation.
- Type consistency: `select_when: str | None`, `selector_catalog() -> str`, `load_selector_guidance(store) -> str`, `build_selection_system_prompt(*, additional_page_limit, selector_guidance)`, user-message key `selector_catalog` — consistent across Tasks 1/2/3/5.
- Known adaptation points named: `page_category` lookup order (Task 1), `JsonWikiPageSelector` stubability (Task 3), existing librarian test assertions (Task 3), `_copy_wiki_root` reuse (Task 5).
