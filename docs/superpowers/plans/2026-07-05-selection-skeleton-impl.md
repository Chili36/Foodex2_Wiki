# Selection Skeleton Failsafe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the code-construction skeleton (base-term / facet / validation coverage, no maintenance/orientation leaks) on every `/wiki/context-pack` response, as a measured failsafe whose every intervention is logged as a selector miss.

**Architecture:** Policy lives in a new markdown page (`selection-policy.md`) with a fenced YAML block; a new pure module `wiki_api/selection_policy.py` parses and enforces it post-selector inside `create_context_pack`; the doctor validates the policy page; the eval runner reports a backfill rate. Spec: `docs/superpowers/specs/2026-07-05-selection-skeleton-design.md`.

**Tech Stack:** Python 3, FastAPI, PyYAML (already a dependency), pytest.

## Global Constraints

- Never change any LLM model name.
- The LLM selector prompt and selector call are NOT modified in this phase.
- The deterministic layer encodes general structural invariants only — never case-specific content (no "query X → page Y" rules).
- Backfill ignores `max_pages` (correctness beats page budget; overruns visible in trace).
- Every backfill logs a `selector_miss` info line and appears in the response trace.
- Only `/wiki/context-pack` is enforced; `/wiki/ask` and `/wiki/policy-pack` untouched.
- `RUNTIME_RULES.md` front-position behavior unchanged; `index.md` presence in `pages_used` unchanged.

---

### Task 1: Policy page + registration

**Files:**
- Create: `raw/efsa-guidance/selection-policy.md`
- Modify: `wiki_api/wiki_store.py` (category map, ~line 113-138 block)
- Modify: `index.md` (Orientation section)
- Test: verification via doctor + one assertion added to `tests/test_selection_policy.py` (created here, extended in Task 2)

**Interfaces:**
- Produces: served page `selection-policy.md` with category `orientation`, containing a fenced ```yaml policy block with keys `skeleton_version`, `required_roles` (mapping role → `{members: [...], default: str}`), `drop_pages` (list of literals/globs). Tasks 2–4 parse exactly this shape.

- [ ] **Step 1: Create the policy page**

Create `raw/efsa-guidance/selection-policy.md` with exactly this content:

````markdown
---
title: "Selection Skeleton Policy"
last_updated: "2026-07-05"
source_tier: "local_policy"
sources:
  - "docs/superpowers/specs/2026-07-05-selection-skeleton-design.md"
related:
  - "[[RUNTIME_RULES]]"
  - "[[base-term-selection]]"
  - "[[facet-coding-rules]]"
  - "[[term-type-facet-constraints]]"
---

# Selection Skeleton Policy

This page defines the deterministic failsafe applied to `/wiki/context-pack`
after the LLM page selector runs. It is maintainer policy, not FoodEx2
coding guidance, and is never projected into coding prompts.

## Why This Exists

Every context-pack case constructs a FoodEx2 code, and constructing a code
always requires base-term guidance, facet guidance, and validation guidance.
That is a structural invariant, not a judgment call. The 2026-07-05 baseline
(`reports/selection-evals/2026-07-05-baseline/`) showed the LLM selector
omitting the validation layer in 10 of 15 packs and leaking maintenance
pages into one.

The service backfills a default page for any uncovered role and drops pages
that never belong in a coding pack. Every backfill is logged as a
`selector_miss` and surfaced in the response trace: the failsafe is also a
scoreboard. Improving the selector (Phase 2) should drive the backfill rate
toward zero.

## Bright Line

The deterministic layer may encode general structural invariants only.
It must never encode case-specific content. "All code-construction packs
carry the three roles" is allowed. "When the query says scallop, add the
domoic-acid page" is forbidden — that is selector judgment, forever.
Domain overlays are deliberately not a required role for the same reason.

## Policy Block

The service parses the following block. The doctor validates that every
member and default is a served prompt-facing page and that non-glob drop
entries exist.

```yaml
skeleton_version: 1
required_roles:
  base_term:
    members:
      - base-term-selection.md
    default: base-term-selection.md
  facet:
    members:
      - facet-coding-rules.md
      - implicit-vs-explicit-facets.md
      - process-facets.md
      - ingredient-facets.md
      - packaging-facets.md
      - code-string-format.md
    default: facet-coding-rules.md
  validation:
    members:
      - term-type-facet-constraints.md
      - validation-rules.md
      - structural-validation.md
      - business-rules.md
      - process-validation-rules.md
    default: term-type-facet-constraints.md
drop_pages:
  - "maintenance-*"
  - "README.md"
  - "PROJECT_CONTEXT.md"
  - "KNOWLEDGE_ARCHITECTURE.md"
  - "WIKI_ARCHITECTURE_FOR_MODELS.md"
  - "INGEST_WORKFLOW.md"
  - "MAINTENANCE_WORKFLOW.md"
  - "SCHEMA.md"
  - "log.md"
  - "selection-policy.md"
```
````

- [ ] **Step 2: Register the page category**

In `wiki_api/wiki_store.py`, inside the page-category dict (the block containing `"policy-contract.md": "runtime",` around line 116), add:

```python
            "selection-policy.md": "orientation",
```

- [ ] **Step 3: Register in index.md**

In `index.md`, at the end of the `## Orientation` section (after the `policy-contract.md` line), add:

```markdown
- [selection-policy.md](raw/efsa-guidance/selection-policy.md): Deterministic skeleton failsafe for context-pack assembly: required base-term/facet/validation roles, backfill defaults, drop rules, and the structural-invariants-only bright line.
```

- [ ] **Step 4: Write the registration test**

Create `tests/test_selection_policy.py`:

```python
from wiki_api.wiki_store import WikiStore


def test_selection_policy_page_is_served_as_orientation():
    store = WikiStore(".")
    assert "selection-policy.md" in store.allowed_page_names()
    assert store.page_category("selection-policy.md") == "orientation"
```

- [ ] **Step 5: Run doctor and tests**

Run: `python -m wiki_api.doctor && python -m pytest tests/test_selection_policy.py -v`
Expected: doctor exits with no new errors (page registered in index + category map); 1 test passes. If the doctor flags anything about the new page (e.g. source-tier or wikilink checks), fix the page frontmatter/links — do not relax the doctor.

- [ ] **Step 6: Commit**

```bash
git add raw/efsa-guidance/selection-policy.md wiki_api/wiki_store.py index.md tests/test_selection_policy.py
git commit -m "feat: add selection skeleton policy page (orientation, YAML policy block)"
```

### Task 2: Policy parsing + enforcement module (TDD)

**Files:**
- Create: `wiki_api/selection_policy.py`
- Test: `tests/test_selection_policy.py` (extend)

**Interfaces:**
- Consumes: `WikiStore.read_page` (existing), the Task 1 policy page.
- Produces (Tasks 3–4 rely on these exact names):
  - `load_selection_policy(store: WikiStore) -> SelectionPolicy` (raises `ValueError` on missing/invalid block)
  - `enforce_skeleton(pages_used: list[str], policy: SelectionPolicy) -> SkeletonResult`
  - `SelectionPolicy(skeleton_version: int, required_roles: tuple[RequiredRole, ...], drop_pages: tuple[str, ...])`
  - `RequiredRole(name: str, members: tuple[str, ...], default: str)`
  - `SkeletonResult(final_pages: list[str], backfilled: list[dict], dropped: list[str], selector_covered_roles: list[str])`
  - `POLICY_PAGE_NAME = "selection-policy.md"`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_selection_policy.py`:

```python
import pytest

from wiki_api.selection_policy import (
    RequiredRole,
    SelectionPolicy,
    enforce_skeleton,
    load_selection_policy,
)

POLICY = SelectionPolicy(
    skeleton_version=1,
    required_roles=(
        RequiredRole(name="base_term", members=("base-term-selection.md",), default="base-term-selection.md"),
        RequiredRole(
            name="facet",
            members=("facet-coding-rules.md", "ingredient-facets.md"),
            default="facet-coding-rules.md",
        ),
        RequiredRole(
            name="validation",
            members=("term-type-facet-constraints.md", "process-validation-rules.md"),
            default="term-type-facet-constraints.md",
        ),
    ),
    drop_pages=("maintenance-*", "README.md"),
)


def test_covered_roles_are_not_backfilled():
    pages = ["index.md", "base-term-selection.md", "ingredient-facets.md", "process-validation-rules.md"]
    result = enforce_skeleton(pages, POLICY)
    assert result.final_pages == pages
    assert result.backfilled == []
    assert result.dropped == []
    assert result.selector_covered_roles == ["base_term", "facet", "validation"]


def test_missing_roles_backfilled_in_role_order():
    result = enforce_skeleton(["index.md", "base-term-selection.md"], POLICY)
    assert result.final_pages == [
        "index.md",
        "base-term-selection.md",
        "facet-coding-rules.md",
        "term-type-facet-constraints.md",
    ]
    assert result.backfilled == [
        {"role": "facet", "page": "facet-coding-rules.md"},
        {"role": "validation", "page": "term-type-facet-constraints.md"},
    ]
    assert result.selector_covered_roles == ["base_term"]


def test_drop_list_literal_and_glob():
    result = enforce_skeleton(
        ["index.md", "base-term-selection.md", "maintenance-2024.md", "README.md",
         "ingredient-facets.md", "term-type-facet-constraints.md"],
        POLICY,
    )
    assert result.dropped == ["maintenance-2024.md", "README.md"]
    assert "maintenance-2024.md" not in result.final_pages
    assert "README.md" not in result.final_pages
    assert result.backfilled == []


def test_drop_then_backfill_when_leak_was_only_coverage():
    result = enforce_skeleton(["index.md", "maintenance-2024.md"], POLICY)
    assert result.dropped == ["maintenance-2024.md"]
    assert [item["role"] for item in result.backfilled] == ["base_term", "facet", "validation"]
    assert result.final_pages == [
        "index.md",
        "base-term-selection.md",
        "facet-coding-rules.md",
        "term-type-facet-constraints.md",
    ]


def test_load_selection_policy_from_wiki(tmp_path=None):
    store = WikiStore(".")
    policy = load_selection_policy(store)
    assert policy.skeleton_version == 1
    role_names = [role.name for role in policy.required_roles]
    assert role_names == ["base_term", "facet", "validation"]
    for role in policy.required_roles:
        assert role.default in role.members
    assert "maintenance-*" in policy.drop_pages
    assert "selection-policy.md" in policy.drop_pages


def test_load_selection_policy_rejects_missing_block(tmp_path):
    root = tmp_path
    (root / "raw" / "efsa-guidance").mkdir(parents=True)
    for name in ("README.md", "PROJECT_CONTEXT.md", "KNOWLEDGE_ARCHITECTURE.md", "SCHEMA.md",
                 "INGEST_WORKFLOW.md", "MAINTENANCE_WORKFLOW.md", "RUNTIME_RULES.md",
                 "index.md", "log.md"):
        (root / name).write_text("---\ntitle: x\n---\n# x\n")
    (root / "raw" / "efsa-guidance" / "selection-policy.md").write_text(
        "---\ntitle: x\n---\n# No policy block here\n"
    )
    store = WikiStore(root)
    with pytest.raises(ValueError, match="policy block"):
        load_selection_policy(store)
```

Note: `test_load_selection_policy_rejects_missing_block` builds a minimal wiki root; if `WikiStore(root)` requires more scaffolding than shown (check `tests/conftest.py` and `WikiStore.__init__` for required files), reuse the existing test fixture pattern for a temp store rather than inventing one.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_selection_policy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_api.selection_policy'` (Task 1's registration test still passes).

- [ ] **Step 3: Implement the module**

Create `wiki_api/selection_policy.py`:

```python
"""Deterministic skeleton failsafe for context-pack page selection.

Policy is defined in markdown (selection-policy.md) and parsed here; this
module encodes general structural invariants only — never case-specific
selection rules. Every backfill is a measured selector miss.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch

import yaml

from .wiki_store import WikiStore

POLICY_PAGE_NAME = "selection-policy.md"
_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class RequiredRole:
    name: str
    members: tuple[str, ...]
    default: str


@dataclass(frozen=True)
class SelectionPolicy:
    skeleton_version: int
    required_roles: tuple[RequiredRole, ...]
    drop_pages: tuple[str, ...]


@dataclass(frozen=True)
class SkeletonResult:
    final_pages: list[str]
    backfilled: list[dict[str, str]]
    dropped: list[str]
    selector_covered_roles: list[str]


def load_selection_policy(store: WikiStore) -> SelectionPolicy:
    page = store.read_page(POLICY_PAGE_NAME)
    match = _YAML_BLOCK_RE.search(page.content)
    if not match:
        raise ValueError(f"{POLICY_PAGE_NAME} has no fenced yaml policy block")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError(f"{POLICY_PAGE_NAME} policy block is not a mapping")
    missing_keys = {"skeleton_version", "required_roles", "drop_pages"} - set(data)
    if missing_keys:
        raise ValueError(f"{POLICY_PAGE_NAME} policy block missing keys: {sorted(missing_keys)}")
    raw_roles = data["required_roles"]
    raw_drop = data["drop_pages"]
    if not isinstance(raw_roles, dict) or not raw_roles:
        raise ValueError(f"{POLICY_PAGE_NAME} required_roles must be a non-empty mapping")
    if not isinstance(raw_drop, list):
        raise ValueError(f"{POLICY_PAGE_NAME} drop_pages must be a list")
    roles: list[RequiredRole] = []
    for role_name, role_data in raw_roles.items():
        members = role_data.get("members") if isinstance(role_data, dict) else None
        default = role_data.get("default") if isinstance(role_data, dict) else None
        if not isinstance(members, list) or not members or not isinstance(default, str):
            raise ValueError(
                f"{POLICY_PAGE_NAME} role {role_name!r} needs a non-empty members list and a default"
            )
        member_names = tuple(str(member) for member in members)
        if default not in member_names:
            raise ValueError(
                f"{POLICY_PAGE_NAME} role {role_name!r} default {default!r} is not among its members"
            )
        roles.append(RequiredRole(name=str(role_name), members=member_names, default=default))
    return SelectionPolicy(
        skeleton_version=int(data["skeleton_version"]),
        required_roles=tuple(roles),
        drop_pages=tuple(str(pattern) for pattern in raw_drop),
    )


def enforce_skeleton(pages_used: list[str], policy: SelectionPolicy) -> SkeletonResult:
    dropped = [
        page
        for page in pages_used
        if any(fnmatch(page, pattern) for pattern in policy.drop_pages)
    ]
    kept = [page for page in pages_used if page not in dropped]
    backfilled: list[dict[str, str]] = []
    covered: list[str] = []
    for role in policy.required_roles:
        if any(page in role.members for page in kept):
            covered.append(role.name)
        else:
            kept.append(role.default)
            backfilled.append({"role": role.name, "page": role.default})
    return SkeletonResult(
        final_pages=kept,
        backfilled=backfilled,
        dropped=dropped,
        selector_covered_roles=covered,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_selection_policy.py -v`
Expected: all pass (7 tests including Task 1's).

- [ ] **Step 5: Commit**

```bash
git add wiki_api/selection_policy.py tests/test_selection_policy.py
git commit -m "feat: parse and enforce selection skeleton policy from markdown"
```

### Task 3: Wire enforcement into /wiki/context-pack (TDD)

**Files:**
- Modify: `wiki_api/app.py` (`create_context_pack`, currently ~lines 1531-1631; imports at top)
- Test: `tests/test_wiki_api.py`

**Interfaces:**
- Consumes: `load_selection_policy`, `enforce_skeleton`, `SkeletonResult` from Task 2.
- Produces: `trace["skeleton_enforcement"]` = `{"policy_version": int, "backfilled": [{"role","page"}...], "dropped": [...], "selector_covered_roles": [...]}` in every context-pack response; a `selector_miss` logger.info line per backfill. Task 5 reads `trace["skeleton_enforcement"]`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_wiki_api.py` (reuse the file's existing client/fixture idiom; the autouse fixture resets `app_module.selector_runner` per test — assign the leaky fake inside the test body). Model the fake on the existing `FakeSelector` class in the same file, changing only `pages_used`/`tool_trace`:

```python
class FakeLeakySelector(FakeSelector):
    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        result = super().run(payload)
        return PageSelectionResult(
            pages_used=["index.md", "base-term-selection.md", "ingredient-facets.md", "maintenance-2024.md"],
            tool_trace=result.tool_trace,
            token_summary=result.token_summary,
            timing_summary=result.timing_summary,
        )


def test_context_pack_backfills_missing_roles_and_drops_leaks() -> None:
    app_module.selector_runner = FakeLeakySelector()
    response = client.post(
        "/wiki/context-pack",
        json={"search_term": "test skeleton enforcement"},
    )
    assert response.status_code == 200
    payload = response.json()
    pages_used = payload["pages_used"]
    assert pages_used[0] == "RUNTIME_RULES.md"
    assert "maintenance-2024.md" not in pages_used
    assert "term-type-facet-constraints.md" in pages_used
    enforcement = payload["trace"]["skeleton_enforcement"]
    assert enforcement["backfilled"] == [
        {"role": "validation", "page": "term-type-facet-constraints.md"}
    ]
    assert enforcement["dropped"] == ["maintenance-2024.md"]
    assert enforcement["selector_covered_roles"] == ["base_term", "facet"]
    page_names = [page["page_name"] for page in payload["pages"]]
    assert "term-type-facet-constraints.md" in page_names
    assert "maintenance-2024.md" not in page_names


def test_context_pack_trace_reports_no_backfill_when_roles_covered() -> None:
    response = client.post(
        "/wiki/context-pack",
        json={"search_term": "test skeleton no-op"},
    )
    assert response.status_code == 200
    enforcement = response.json()["trace"]["skeleton_enforcement"]
    assert enforcement["backfilled"] == []
    assert enforcement["dropped"] == []
```

(The default `FakeSelector` already covers all three roles — base-term-selection, ingredient-facets et al., term-type-facet-constraints — so the second test asserts the no-op path.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_wiki_api.py -k "skeleton" -v`
Expected: FAIL with `KeyError: 'skeleton_enforcement'` (both tests).

- [ ] **Step 3: Implement the integration**

In `wiki_api/app.py`:

Add to imports (near the other `wiki_api` imports):

```python
from .selection_policy import enforce_skeleton, load_selection_policy
```

In `create_context_pack`, immediately after the `selection_result = runner.run(payload)` try/except block, insert:

```python
    try:
        selection_policy = load_selection_policy(store)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=f"selection policy unavailable: {exc}") from exc
    skeleton = enforce_skeleton(selection_result.pages_used, selection_policy)
    for backfill in skeleton.backfilled:
        logger.info(
            "selector_miss %s",
            json.dumps(
                {
                    "surface": "context-pack",
                    "search_term": request.search_term,
                    "role": backfill["role"],
                    "page": backfill["page"],
                },
                ensure_ascii=False,
            ),
        )
```

Then replace the two uses of `selection_result.pages_used` in the page assembly with `skeleton.final_pages`:

```python
    pages = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            category=store.page_category(page.name),
            source_tier=page.source_tier,
            sources=page.sources,
            related=page.related,
            content=store.prompt_content_for_context_pack(page) if request.include_page_content else None,
        )
        for page in [store.read_page(page_name) for page_name in skeleton.final_pages]
    ]
    final_pages_used, pages = _ensure_front_page(
        RUNTIME_RULES_PAGE_NAME,
        skeleton.final_pages,
        pages,
        include_content=request.include_page_content,
        content_for_page=store.prompt_content_for_context_pack,
    )
```

And add to the response `trace` dict (after the `"prompt_projection"` entry):

```python
            "skeleton_enforcement": {
                "policy_version": selection_policy.skeleton_version,
                "backfilled": skeleton.backfilled,
                "dropped": skeleton.dropped,
                "selector_covered_roles": skeleton.selector_covered_roles,
            },
```

- [ ] **Step 4: Run tests to verify they pass, then the full suite**

Run: `python -m pytest tests/test_wiki_api.py -k "skeleton" -v && python -m pytest`
Expected: skeleton tests pass; full suite green (existing context-pack tests unaffected — the default FakeSelector covers all roles, so enforcement is a no-op for them; if any existing test asserts the exact `trace` key set, update it to include `skeleton_enforcement`).

- [ ] **Step 5: Commit**

```bash
git add wiki_api/app.py tests/test_wiki_api.py
git commit -m "feat: enforce selection skeleton on /wiki/context-pack with selector-miss logging"
```

### Task 4: Doctor validation of the policy page (TDD)

**Files:**
- Modify: `wiki_api/doctor.py`
- Test: `tests/test_wiki_doctor.py`

**Interfaces:**
- Consumes: `load_selection_policy`, `POLICY_PAGE_NAME` from Task 2; `PROMPT_CONTEXT_PAGE_CATEGORIES` from `wiki_api.wiki_store`; existing `DoctorIssue` dataclass and `run_doctor` check-list pattern.
- Produces: doctor check name `"selection_policy"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_wiki_doctor.py` (follow the file's existing fixture pattern for building/copying a wiki root; the test below assumes a helper that copies the real wiki to `tmp_path` — reuse whatever idiom the file already uses for corrupting a page and running the doctor):

```python
def test_doctor_flags_corrupted_selection_policy(tmp_path):
    root = _copy_wiki_root(tmp_path)  # reuse/adapt the file's existing copy helper
    policy_path = root / "raw" / "efsa-guidance" / "selection-policy.md"
    policy_path.write_text(
        "---\ntitle: \"Selection Skeleton Policy\"\nlast_updated: \"2026-07-05\"\n"
        "source_tier: \"local_policy\"\n---\n\n# Selection Skeleton Policy\n\nNo block.\n"
    )
    report = run_doctor(root)
    checks = {issue.check for issue in report.errors}
    assert "selection_policy" in checks


def test_doctor_passes_selection_policy_on_real_wiki():
    report = run_doctor(".")
    assert "selection_policy" not in {issue.check for issue in report.errors}
```

If `run_doctor`'s signature differs (check `wiki_api/doctor.py:81`), adapt the call — do not change `run_doctor`'s signature.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_wiki_doctor.py -k "selection_policy" -v`
Expected: first test FAILS (no `selection_policy` check exists yet); second passes vacuously.

- [ ] **Step 3: Implement the doctor check**

In `wiki_api/doctor.py`, add imports:

```python
from .selection_policy import POLICY_PAGE_NAME, load_selection_policy
from .wiki_store import PROMPT_CONTEXT_PAGE_CATEGORIES
```

(If `wiki_store` imports already exist, extend them.) Add the check function alongside the other `_check_*` functions:

```python
def _check_selection_policy(store: WikiStore) -> Iterable[DoctorIssue]:
    issues: list[DoctorIssue] = []
    try:
        policy = load_selection_policy(store)
    except Exception as exc:
        issues.append(
            DoctorIssue(
                severity="error",
                check="selection_policy",
                location=POLICY_PAGE_NAME,
                message=f"policy block unreadable: {exc}",
            )
        )
        return issues
    served = store.allowed_page_names()
    for role in policy.required_roles:
        for member in role.members:
            if member not in served:
                issues.append(
                    DoctorIssue(
                        severity="error",
                        check="selection_policy",
                        location=POLICY_PAGE_NAME,
                        message=f"role {role.name!r} member {member!r} is not a served page",
                    )
                )
            elif store.page_category(member) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
                issues.append(
                    DoctorIssue(
                        severity="error",
                        check="selection_policy",
                        location=POLICY_PAGE_NAME,
                        message=f"role {role.name!r} member {member!r} is not prompt-facing",
                    )
                )
    for pattern in policy.drop_pages:
        if "*" not in pattern and pattern not in served:
            issues.append(
                DoctorIssue(
                    severity="error",
                    check="selection_policy",
                    location=POLICY_PAGE_NAME,
                    message=f"drop_pages entry {pattern!r} is not a served page",
                )
            )
    return issues
```

Wire it into `run_doctor` next to the other checks:

```python
    issues.extend(_check_selection_policy(store))
```

- [ ] **Step 4: Run tests to verify they pass, then doctor + full suite**

Run: `python -m pytest tests/test_wiki_doctor.py -v && python -m wiki_api.doctor && python -m pytest`
Expected: doctor tests pass; live doctor exits clean; full suite green.

- [ ] **Step 5: Commit**

```bash
git add wiki_api/doctor.py tests/test_wiki_doctor.py
git commit -m "feat: doctor validates selection skeleton policy page"
```

### Task 5: Backfill-rate metric + Phase 1 eval run

**Files:**
- Modify: `scripts/selection_eval.py`
- Create (runner output + analysis): `reports/selection-evals/<date>-phase1/results.json`, `reports/selection-evals/<date>-phase1/triage.md`
- Modify: `log.md`

**Interfaces:**
- Consumes: `trace["skeleton_enforcement"]` from Task 3.
- Produces: summary keys `backfill_case_rate` (fraction of cases with ≥1 backfill) and `mean_backfills_per_case`; per-case row keys `backfilled`, `dropped`.

- [ ] **Step 1: Extend the runner**

In `scripts/selection_eval.py`, inside the case loop after `score = score_case(...)`, add enforcement fields to the row:

```python
        enforcement = (response.get("trace") or {}).get("skeleton_enforcement") or {}
        rows.append(
            {
                "id": case["id"],
                "reviewed": bool(case.get("reviewed")),
                "pages_used": pages_used,
                "pack_chars": pack_chars,
                "selector_tokens": (response.get("trace") or {}).get("token_summary"),
                "backfilled": enforcement.get("backfilled", []),
                "dropped": enforcement.get("dropped", []),
                **score,
            }
        )
```

(Replace the existing `rows.append({...})` — same dict plus the two new keys.) After `summary = aggregate(rows)` add:

```python
    summary["backfill_case_rate"] = (
        len([row for row in rows if row["backfilled"]]) / len(rows) if rows else 0
    )
    summary["mean_backfills_per_case"] = (
        sum(len(row["backfilled"]) for row in rows) / len(rows) if rows else 0
    )
```

And extend the per-case print line so misses stay visible:

```python
        print(
            f"{case['id']}: recall={score['must_have_recall']:.2f} "
            f"leaks={score['leaks']} missing={score['missing']} "
            f"backfilled={[item['page'] for item in row['backfilled']]}"
        )
```

(Adjust variable naming to match the final loop body — the printed row must be the one just appended.)

- [ ] **Step 2: Run the Phase 1 eval against the live API**

Start the API if not running (`uvicorn wiki_api.app:app --port 8010`; `.env` supplies keys; if port 8010 already serves `/health`, reuse it). Then:

Run: `python scripts/selection_eval.py --label phase1 --only-reviewed`
Expected: 15 case lines; summary now includes `backfill_case_rate` and `mean_backfills_per_case`; recall materially above the 0.73 baseline; `leak_free_rate` 1.0. Results under `reports/selection-evals/<date>-phase1/`.

- [ ] **Step 3: Write the comparison triage**

Create `reports/selection-evals/<date>-phase1/triage.md` with: metric table baseline vs phase1 (recall, precision, leak-free, pack chars, backfill_case_rate, mean_backfills_per_case), which baseline misses closed, which remain (expected residuals: SEL-0005 `process-validation-rules.md`, SEL-0011 `implicit-vs-explicit-facets.md` — these are Phase 2 candidate-signal evidence, plus any surprises), and one paragraph assessing the acceptance criteria from the spec (leak-free 1.0, recall ≥ ~0.90, no precision collapse, selector tokens unchanged, backfill rate reported).

- [ ] **Step 4: Update log.md**

Add a new entry at the top of `log.md` (below the `# Log` heading), dated with the run date, category `maintenance`, titled "Selection skeleton failsafe for context-pack", noting: policy page added, enforcement + selector-miss logging live on `/wiki/context-pack`, doctor check added, and the phase1 vs baseline numbers with the backfill rate as the new selector scoreboard.

- [ ] **Step 5: Run full suite once more and commit**

Run: `python -m pytest && python -m wiki_api.doctor`
Expected: green, doctor clean.

```bash
git add scripts/selection_eval.py reports/selection-evals/ log.md
git commit -m "feat: report skeleton backfill rate and record phase1 selection eval"
```

---

## Self-Review Notes

- Spec coverage: policy page (Task 1), parsing/enforcement (Task 2), integration + trace + selector_miss logging (Task 3), doctor (Task 4), eval metric + phase1 run + acceptance assessment (Task 5). Out-of-scope items from the spec have no tasks, as intended.
- Type consistency: `load_selection_policy`/`enforce_skeleton`/`SkeletonResult` names and shapes match across Tasks 2, 3, 4; trace key `skeleton_enforcement` matches between Tasks 3 and 5.
- Known adaptation points are named explicitly (doctor fixture helper, `run_doctor` signature, existing rows.append replacement) rather than left vague.
