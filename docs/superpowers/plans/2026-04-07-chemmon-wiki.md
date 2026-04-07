# ChemMon Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone ChemMon Wiki repo by forking the FoodEx2 wiki, stripping domain-specific content, and replacing it with a simple Q&A API (`/wiki/ask`) backed by a two-stage LLM flow (page selector + answerer).

**Architecture:** Fork-and-adapt from `Chili36/Foodex2_Wiki`. Keep `WikiStore` and page selector infrastructure. Drop solver, policy-pack, context-pack, and all candidate models. Add a single `/wiki/ask` endpoint with `AskRequest`/`AskResponse` models backed by a new `AnthropicChemMonAnswerer` class.

**Tech Stack:** Python 3.12, FastAPI, Anthropic SDK, PyYAML, python-dotenv, pytest, httpx (test client)

**Source repo:** `Chili36/Foodex2_Wiki` (current branch: `wiki/writing-quality-pass`)

---

### Task 1: Fork repo and strip FoodEx2 content

**Files:**
- Delete: `foodex2_docs/` (all PDFs)
- Delete: `raw/efsa-guidance/` (all wiki pages)
- Delete: `docs/` (specs from FoodEx2 project)
- Create: `chemmon_docs/` (empty directory with `.gitkeep`)
- Create: `raw/chemmon-guidance/` (empty directory with `.gitkeep`)
- Modify: `index.md`
- Modify: `log.md`
- Modify: `PROJECT_CONTEXT.md`
- Modify: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Fork the repo on GitHub**

```bash
gh repo fork Chili36/Foodex2_Wiki --clone --fork-name ChemMon_Wiki
cd ChemMon_Wiki
git checkout -b main
```

- [ ] **Step 2: Remove FoodEx2 content directories**

```bash
rm -rf foodex2_docs/
rm -rf raw/efsa-guidance/
rm -rf docs/
```

- [ ] **Step 3: Create ChemMon content directories**

```bash
mkdir -p chemmon_docs
touch chemmon_docs/.gitkeep
mkdir -p raw/chemmon-guidance
touch raw/chemmon-guidance/.gitkeep
```

- [ ] **Step 4: Replace index.md**

```markdown
---
title: "Wiki Index"
last_updated: "2026-04-07"
---

# Index

This is the content-oriented catalog for the ChemMon reporting guidance wiki layer.

## Orientation

- [README.md](README.md): Repo overview, current status, directory layout, and working conventions.
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): What this wiki is for, why it exists, and the LLM-wiki operating model behind it.
- [log.md](log.md): Chronological record of ingests and maintenance work.

## Guiding Principles

- Chemical monitoring reporting follows EFSA's annual call for data and the associated guidance documents. Code and report samples according to the current year's guidance, not prior years.
- When the guidance is ambiguous, prefer the interpretation that maintains data quality and regulatory compliance over the one that is easier to implement.
- Business rules (CHEMMON01-CHEMMON12+) are the authoritative validation layer. If a business rule and a prose section of the guidance conflict, the business rule takes precedence.
- Reporting domains (chemical DCF, biological/zoonoses DCF) have specific routing rules. Not all parameters belong in the same domain.

## ChemMon Guidance

(Pages will appear here as source documents are ingested.)

## Source Layer

- [chemmon_docs](chemmon_docs): Immutable EFSA PDF source collection used to build and verify the wiki.
```

- [ ] **Step 5: Replace log.md**

```markdown
---
title: "Wiki Log"
last_updated: "2026-04-07"
---

# Log

## [2026-04-07] setup | Initial ChemMon wiki repo

- Forked from the FoodEx2 wiki repo and stripped all FoodEx2-specific content.
- Created empty source and guidance directories.
- Adapted the API to a Q&A service with a single `/wiki/ask` endpoint.
```

- [ ] **Step 6: Replace PROJECT_CONTEXT.md**

```markdown
---
title: "Project Context"
last_updated: "2026-04-07"
source_inspiration:
  - "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
---

# What We Are Building

A persistent markdown knowledge base for EFSA Chemical Monitoring reporting guidance so an LLM can support ChemMon reporting questions from a maintained body of structured knowledge instead of re-reading raw guidance PDFs from scratch each time.

In this workspace, that means:

- `chemmon_docs/` holds the immutable source PDFs.
- `raw/chemmon-guidance/` holds the LLM-maintained markdown pages extracted, organized, cross-linked, and kept concise for both human reading and machine use.
- The knowledge base is topic-oriented rather than document-oriented, so rules about reporting domains, mandatory facets, business rules, and submission procedures live in dedicated pages instead of a single large dump.

# Why We Are Building It

The goal is not simple document retrieval. The goal is to compile knowledge once, preserve the synthesis, and keep improving it over time.

Why this matters for ChemMon:

- ChemMon reporting guidance is updated annually and contains domain-specific rules that interact with each other.
- Many reporting questions require combining rules from multiple sections of the guidance, plus EFSA clarifications that live only in Teams channels.
- A maintained wiki reduces repeated interpretation work, surfaces contradictions or edge cases earlier, and makes downstream reporting more consistent.
- Structured markdown pages are easier for an LLM to search, update, cite, and cross-reference than raw PDFs or one-off chat history.

# Operating Model

- New source documents are added to the raw source layer first.
- The LLM reads them, extracts the durable rules, and updates the markdown knowledge base.
- The markdown layer becomes the default working context for answering questions, while the raw PDFs remain the source of truth for verification.
- EFSA official clarifications from the reporting Teams channel are ingested as they arrive.

# Design Principle

This project follows the general pattern described in Andrej Karpathy's `llm-wiki` gist published on April 4, 2026: raw sources stay immutable, while the LLM incrementally builds and maintains a persistent interlinked wiki that compounds in value over time.
```

- [ ] **Step 7: Replace README.md**

```markdown
# ChemMon Wiki

This repository contains a structured markdown knowledge base for EFSA Chemical Monitoring reporting guidance.

It follows the "LLM wiki" pattern: raw source documents stay immutable, while an LLM incrementally builds and maintains a topic-oriented markdown layer that is easier to read, search, cite, and update over time.

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for the project rationale.

## Directory Layout

\`\`\`text
chemmon_docs/
  Raw EFSA PDF sources (annual ChemMon reporting guidance)

raw/chemmon-guidance/
  Topic-oriented markdown knowledge pages derived from the guidance PDFs
  and EFSA official clarifications

wiki_api/
  FastAPI service exposing the wiki catalog, raw page reads, and
  a Q&A endpoint for answering ChemMon reporting questions
\`\`\`

## Page Conventions

Each wiki page should:

- Use YAML frontmatter
- List source PDFs or clarification references
- Include related-page links
- Keep source-page comments such as \`<!-- Source: ... -->\`
- Stay concise and scannable
- Attribute claims to source pages or sections
- Prefer topic pages over document dumps

## Wiki API

Create and use the repo-local environment:

\`\`\`bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
\`\`\`

Copy and edit the environment file:

\`\`\`bash
cp .env.example .env
\`\`\`

Set at least:

\`\`\`bash
ANTHROPIC_API_KEY=...
WIKI_SELECTOR_MODEL=claude-3-7-sonnet-latest
WIKI_ANSWERER_MODEL=claude-3-7-sonnet-latest
\`\`\`

Run it locally with:

\`\`\`bash
. .venv/bin/activate
uvicorn wiki_api.app:app --reload --port 8005
\`\`\`

Main endpoints:

- \`GET /health\`: service health check
- \`GET /wiki/index\`: raw \`index.md\`
- \`GET /wiki/pages\`: page catalog with titles and summaries
- \`GET /wiki/pages/{page_name}\`: one wiki page
- \`GET /wiki/view\`: browser-based wiki viewer
- \`POST /wiki/ask\`: ask a question, get a grounded answer with citations

Run tests with:

\`\`\`bash
. .venv/bin/activate
pytest -q
\`\`\`
```

- [ ] **Step 8: Replace .env.example**

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
WIKI_SELECTOR_MODEL=claude-3-7-sonnet-latest
WIKI_ANSWERER_MODEL=claude-3-7-sonnet-latest
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "Strip FoodEx2 content and set up ChemMon wiki structure"
```

---

### Task 2: Rewrite wiki_store.py for ChemMon

**Files:**
- Modify: `wiki_api/wiki_store.py`
- Modify: `wiki_api/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_store.py`:

```python
from __future__ import annotations

from pathlib import Path

from wiki_api.wiki_store import WikiStore


def _store() -> WikiStore:
    return WikiStore(Path("."))


def test_store_reads_index() -> None:
    store = _store()
    page = store.read_page("index.md")
    assert page.name == "index.md"
    assert page.title == "Wiki Index"
    assert page.content.startswith("---")


def test_store_lists_no_pages_before_ingest() -> None:
    store = _store()
    pages = store.list_pages()
    assert pages == []


def test_store_catalog_empty_before_ingest() -> None:
    store = _store()
    catalog = store.catalog()
    assert catalog == []


def test_store_guiding_principles_extracted() -> None:
    store = _store()
    principles = store.guiding_principles()
    assert len(principles) >= 3
    assert any("business rule" in p.lower() for p in principles)


def test_store_unknown_page_raises() -> None:
    store = _store()
    try:
        store.read_page("nonexistent.md")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_wiki_store.py -v
```

Expected: FAIL because `wiki_store.py` still references `raw/efsa-guidance/`.

- [ ] **Step 3: Update wiki_store.py**

Change the guidance directory path from `raw/efsa-guidance` to `raw/chemmon-guidance`:

```python
class WikiStore:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.guidance_dir = self.root / "raw" / "chemmon-guidance"
        self.index_path = self.root / "index.md"
        self.log_path = self.root / "log.md"
```

No other changes needed. The rest of `WikiStore` is generic.

- [ ] **Step 4: Update __init__.py**

```python
"""ChemMon wiki retrieval API package."""
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_wiki_store.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add wiki_api/wiki_store.py wiki_api/__init__.py tests/test_wiki_store.py
git commit -m "Adapt WikiStore for ChemMon guidance directory"
```

---

### Task 3: Create the page selector module

**Files:**
- Create: `wiki_api/page_selector.py`
- Delete: `wiki_api/librarian.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_page_selector.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from wiki_api.page_selector import AnthropicWikiPageSelector
from wiki_api.wiki_store import WikiStore


def _response(*, stop_reason: str, content: list[dict[str, object]], input_tokens: int, output_tokens: int):
    return {
        "stop_reason": stop_reason,
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


class FakeMessages:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeAnthropicClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.messages = FakeMessages(responses)


def _store() -> WikiStore:
    return WikiStore(Path("."))


def test_selector_picks_pages_via_tool_use() -> None:
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="tool_use",
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "read_wiki_pages",
                        "input": {"page_names": []},
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            )
        ]
    )

    selector = AnthropicWikiPageSelector(
        store=_store(), client=client, model="fake-model", max_pages=6
    )
    result = selector.run({"question": "What are the VMPR reporting rules?"})

    assert "index.md" in result.pages_used
    assert result.token_summary["calls"] == 1

    first_call = client.messages.calls[0]
    assert "ChemMon" in first_call["system"]
    payload = json.loads(first_call["messages"][0]["content"])
    assert "question" in payload
    assert "wiki_index" in payload


def test_selector_accepts_json_page_names_without_tool() -> None:
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="end_turn",
                content=[
                    {
                        "type": "text",
                        "text": json.dumps({"page_names": []}),
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            )
        ]
    )

    selector = AnthropicWikiPageSelector(
        store=_store(), client=client, model="fake-model", max_pages=6
    )
    result = selector.run({"question": "test"})

    assert "index.md" in result.pages_used
    assert result.token_summary["calls"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_page_selector.py -v
```

Expected: FAIL because `wiki_api/page_selector.py` does not exist.

- [ ] **Step 3: Create page_selector.py**

Extract `AnthropicWikiPageSelector` and its supporting functions from `librarian.py` into a new `page_selector.py`. Adapt the system prompt for ChemMon:

```python
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from anthropic import Anthropic
from dotenv import load_dotenv

from .wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


READ_WIKI_PAGES_TOOL = {
    "name": "read_wiki_pages",
    "description": (
        "Read one or more non-index pages from the local ChemMon wiki by filename. "
        "Use this to batch the page reads you need after reviewing the provided index."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "page_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Wiki filenames to read.",
            }
        },
        "required": ["page_names"],
    },
}

TOOLS = [READ_WIKI_PAGES_TOOL]

SELECTION_SYSTEM_PROMPT = """You are the ChemMon wiki page selector.

Your only job is to choose which wiki pages should be returned as context for the user's question about chemical monitoring reporting.

Rules:
- The full catalog from `index.md` is already provided in the user message.
- Use that catalog first to decide which pages matter.
- Do not request `index.md` again.
- Do not answer the question.
- Request the minimal set of non-index pages needed for this question.
- When possible, request all needed pages in a single `read_wiki_pages` call.
- You may request at most 5 non-index pages.
- If no additional pages are needed, return JSON only: {"page_names": []}
"""


class AnthropicMessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClientProtocol(Protocol):
    @property
    def messages(self) -> AnthropicMessagesClient: ...


@dataclass(frozen=True)
class PageSelectionResult:
    pages_used: list[str]
    tool_trace: list[dict[str, Any]]
    token_summary: dict[str, Any]
    timing_summary: dict[str, Any]


def _get_block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _response_text(content_blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        if _get_block_value(block, "type") == "text":
            parts.append(_get_block_value(block, "text", ""))
    return "".join(parts).strip()


def _extract_json_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Empty response from page selector")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        return json.loads(text[brace_start : brace_end + 1])
    raise ValueError("Could not extract JSON from page selector response")


def _usage_dict(usage: Any, *, stop_reason: str | None) -> dict[str, int | str | None]:
    input_tokens = int(_get_block_value(usage, "input_tokens", 0) or 0)
    output_tokens = int(_get_block_value(usage, "output_tokens", 0) or 0)
    cache_creation = int(_get_block_value(usage, "cache_creation_input_tokens", 0) or 0)
    cache_read = int(_get_block_value(usage, "cache_read_input_tokens", 0) or 0)
    return {
        "stop_reason": stop_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "total_tracked_tokens": input_tokens + output_tokens + cache_creation + cache_read,
    }


def _aggregate_usage(usages: list[dict[str, int | str | None]], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "calls": len(usages),
        "input_tokens": sum(int(u["input_tokens"]) for u in usages),
        "output_tokens": sum(int(u["output_tokens"]) for u in usages),
        "cache_creation_input_tokens": sum(int(u["cache_creation_input_tokens"]) for u in usages),
        "cache_read_input_tokens": sum(int(u["cache_read_input_tokens"]) for u in usages),
        "total_tracked_tokens": sum(int(u["total_tracked_tokens"]) for u in usages),
        "per_call": usages,
    }


def _aggregate_timing(timings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "calls": len(timings),
        "llm_time_ms": sum(int(t["duration_ms"]) for t in timings),
        "per_call": timings,
    }


def _read_pages_payload(
    *,
    store: WikiStore,
    requested_page_names: list[str],
    max_pages: int,
    pages_read: list[str],
    tool_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    max_followup_pages = max(max_pages - 1, 0)
    seen_in_request: set[str] = set()

    for raw_name in requested_page_names:
        page_name = str(raw_name)
        if page_name in seen_in_request:
            skipped.append({"page_name": page_name, "reason": "duplicate_in_request"})
            continue
        seen_in_request.add(page_name)

        if page_name == "index.md":
            skipped.append({"page_name": page_name, "reason": "index_already_provided"})
            continue

        if len(pages_read) >= max_followup_pages:
            skipped.append({"page_name": page_name, "reason": "page_limit_exceeded", "limit": max_pages})
            continue

        try:
            page = store.read_page(page_name)
            normalized_name = store.normalize_page_name(page_name)
            if normalized_name in pages_read:
                skipped.append({"page_name": normalized_name, "reason": "already_read_in_conversation"})
                continue
            pages_read.append(normalized_name)
            tool_trace.append({"page_name": normalized_name, "order": len(tool_trace) + 1, "chars": len(page.content), "synthetic": False})
            pages.append({"page_name": normalized_name, "content": page.content})
        except Exception as exc:
            errors.append({"page_name": page_name, "reason": "read_failed", "message": str(exc)})
            tool_trace.append({"page_name": page_name, "order": len(tool_trace) + 1, "chars": len(str(exc)), "synthetic": True})

    return {"pages": pages, "skipped": skipped, "errors": errors}


def _selection_payload_from_response(content: list[Any]) -> list[str]:
    tool_uses = [b for b in content if _get_block_value(b, "type") == "tool_use"]
    if tool_uses:
        page_names: list[str] = []
        for block in tool_uses:
            raw = _get_block_value(block, "input", {}).get("page_names", [])
            if not isinstance(raw, list):
                raw = [raw]
            page_names.extend(str(name) for name in raw)
        return page_names
    final_text = _response_text(content)
    data = _extract_json_payload(final_text)
    raw = data.get("page_names", [])
    if not isinstance(raw, list):
        raw = [raw]
    return [str(name) for name in raw]


def build_anthropic_client() -> AnthropicClientProtocol:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


def _resolve_model(*env_keys: str, default: str) -> str:
    for key in env_keys:
        value = os.getenv(key)
        if value:
            return value
    return default


class AnthropicWikiPageSelector:
    def __init__(
        self,
        *,
        store: WikiStore,
        client: AnthropicClientProtocol | None = None,
        model: str | None = None,
        max_pages: int = 6,
        max_tokens: int = 1500,
    ):
        self.store = store
        self.client = client or build_anthropic_client()
        self.model = model or _resolve_model("WIKI_SELECTOR_MODEL", default="claude-3-7-sonnet-latest")
        self.max_pages = max_pages
        self.max_tokens = max_tokens

    def run(self, payload: dict[str, Any]) -> PageSelectionResult:
        selector_started = time.perf_counter()
        index_content = self.store.read_page("index.md").content
        llm_started = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SELECTION_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": payload["question"], "wiki_index": index_content},
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        llm_duration_ms = int((time.perf_counter() - llm_started) * 1000)
        timing_trace = [{"call_number": 1, "duration_ms": llm_duration_ms, "stop_reason": _get_block_value(response, "stop_reason")}]
        usage_trace = [_usage_dict(_get_block_value(response, "usage"), stop_reason=_get_block_value(response, "stop_reason"))]
        content = _get_block_value(response, "content", [])
        selected_page_names = _selection_payload_from_response(content)
        pages_read: list[str] = []
        tool_trace: list[dict[str, Any]] = []
        _read_pages_payload(
            store=self.store,
            requested_page_names=selected_page_names,
            max_pages=self.max_pages,
            pages_read=pages_read,
            tool_trace=tool_trace,
        )
        return PageSelectionResult(
            pages_used=list(dict.fromkeys(["index.md", *pages_read])),
            tool_trace=tool_trace,
            token_summary=_aggregate_usage(usage_trace, self.model),
            timing_summary={
                **_aggregate_timing(timing_trace),
                "selector_wall_time_ms": int((time.perf_counter() - selector_started) * 1000),
            },
        )
```

- [ ] **Step 4: Delete librarian.py**

```bash
rm wiki_api/librarian.py
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_page_selector.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add wiki_api/page_selector.py tests/test_page_selector.py
git add -u  # picks up deleted librarian.py
git commit -m "Add ChemMon page selector, remove FoodEx2 librarian"
```

---

### Task 4: Create the answerer module

**Files:**
- Create: `wiki_api/answerer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_answerer.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from wiki_api.answerer import AnthropicChemMonAnswerer


def _response(*, stop_reason: str, content: list[dict[str, object]], input_tokens: int, output_tokens: int):
    return {
        "stop_reason": stop_reason,
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


class FakeMessages:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeAnthropicClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.messages = FakeMessages(responses)


def test_answerer_returns_answer_with_citations() -> None:
    answer_payload = {
        "answer": "Yes, F33 is mandatory for acrylamide even when implicit.",
        "citations": ["acrylamide-rules.md"],
    }
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="end_turn",
                content=[{"type": "text", "text": json.dumps(answer_payload)}],
                input_tokens=200,
                output_tokens=50,
            )
        ]
    )

    answerer = AnthropicChemMonAnswerer(client=client, model="fake-model")
    result = answerer.run(
        question="Do I need F33 for acrylamide?",
        pages=[
            {"page_name": "acrylamide-rules.md", "content": "F33 is mandatory for acrylamide."},
        ],
    )

    assert result.answer == "Yes, F33 is mandatory for acrylamide even when implicit."
    assert result.citations == ["acrylamide-rules.md"]
    assert result.token_summary["calls"] == 1
    assert result.timing_summary["answerer_wall_time_ms"] >= 0

    first_call = client.messages.calls[0]
    assert "ChemMon" in first_call["system"]
    payload = json.loads(first_call["messages"][0]["content"])
    assert payload["question"] == "Do I need F33 for acrylamide?"
    assert len(payload["pages"]) == 1


def test_answerer_handles_plain_text_response() -> None:
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="end_turn",
                content=[{"type": "text", "text": "The wiki does not cover this topic."}],
                input_tokens=200,
                output_tokens=30,
            )
        ]
    )

    answerer = AnthropicChemMonAnswerer(client=client, model="fake-model")
    result = answerer.run(
        question="What is the meaning of life?",
        pages=[],
    )

    assert result.answer == "The wiki does not cover this topic."
    assert result.citations == []
    assert result.token_summary["calls"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_answerer.py -v
```

Expected: FAIL because `wiki_api/answerer.py` does not exist.

- [ ] **Step 3: Create answerer.py**

```python
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from anthropic import Anthropic
from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

ANSWERER_SYSTEM_PROMPT = """You are the ChemMon wiki assistant.

Your job is to answer questions about EFSA Chemical Monitoring reporting using only the provided wiki pages.

Rules:
- Answer based solely on the provided wiki page content.
- Cite which page each claim comes from using the page filename.
- If the wiki pages do not contain enough information to answer the question, say so clearly.
- Do not make up rules or guidance that is not in the provided pages.
- Be concise and direct.

Return JSON only with this structure:
{
  "answer": "Your grounded answer here.",
  "citations": ["page-name.md", "other-page.md"]
}

If you cannot answer from the provided pages, return:
{
  "answer": "The wiki does not cover this topic.",
  "citations": []
}
"""


class AnthropicMessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClientProtocol(Protocol):
    @property
    def messages(self) -> AnthropicMessagesClient: ...


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    citations: list[str]
    token_summary: dict[str, Any]
    timing_summary: dict[str, Any]


def _get_block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _response_text(content_blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        if _get_block_value(block, "type") == "text":
            parts.append(_get_block_value(block, "text", ""))
    return "".join(parts).strip()


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _usage_dict(usage: Any, *, stop_reason: str | None) -> dict[str, int | str | None]:
    input_tokens = int(_get_block_value(usage, "input_tokens", 0) or 0)
    output_tokens = int(_get_block_value(usage, "output_tokens", 0) or 0)
    cache_creation = int(_get_block_value(usage, "cache_creation_input_tokens", 0) or 0)
    cache_read = int(_get_block_value(usage, "cache_read_input_tokens", 0) or 0)
    return {
        "stop_reason": stop_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "total_tracked_tokens": input_tokens + output_tokens + cache_creation + cache_read,
    }


def _resolve_model(*env_keys: str, default: str) -> str:
    for key in env_keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def build_anthropic_client() -> AnthropicClientProtocol:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


class AnthropicChemMonAnswerer:
    def __init__(
        self,
        *,
        client: AnthropicClientProtocol | None = None,
        model: str | None = None,
        max_tokens: int = 2000,
    ):
        self.client = client or build_anthropic_client()
        self.model = model or _resolve_model("WIKI_ANSWERER_MODEL", default="claude-3-7-sonnet-latest")
        self.max_tokens = max_tokens

    def run(
        self,
        question: str,
        pages: list[dict[str, Any]],
    ) -> AnswerResult:
        answerer_started = time.perf_counter()
        llm_started = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=ANSWERER_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"question": question, "pages": pages},
                        ensure_ascii=False,
                    ),
                }
            ],
        )
        llm_duration_ms = int((time.perf_counter() - llm_started) * 1000)
        usage = _usage_dict(
            _get_block_value(response, "usage"),
            stop_reason=_get_block_value(response, "stop_reason"),
        )
        final_text = _response_text(_get_block_value(response, "content", []))
        data = _extract_json_payload(final_text)
        if data and "answer" in data:
            answer = data["answer"]
            citations = data.get("citations", [])
        else:
            answer = final_text
            citations = []

        return AnswerResult(
            answer=answer,
            citations=citations,
            token_summary={
                "model": self.model,
                "calls": 1,
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cache_creation_input_tokens": usage["cache_creation_input_tokens"],
                "cache_read_input_tokens": usage["cache_read_input_tokens"],
                "total_tracked_tokens": usage["total_tracked_tokens"],
                "per_call": [usage],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": llm_duration_ms,
                "answerer_wall_time_ms": int((time.perf_counter() - answerer_started) * 1000),
                "per_call": [
                    {
                        "call_number": 1,
                        "duration_ms": llm_duration_ms,
                        "stop_reason": _get_block_value(response, "stop_reason"),
                    }
                ],
            },
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_answerer.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add wiki_api/answerer.py tests/test_answerer.py
git commit -m "Add ChemMon answerer module"
```

---

### Task 5: Rewrite app.py with the /wiki/ask endpoint

**Files:**
- Modify: `wiki_api/app.py`
- Delete: `wiki_api/policy.py`
- Delete: `tests/test_wiki_api.py`
- Delete: `tests/test_librarian.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_app.py`:

```python
from __future__ import annotations

import asyncio

import httpx

import wiki_api.app as app_module
from wiki_api.page_selector import PageSelectionResult
from wiki_api.answerer import AnswerResult


async def _request(method: str, path: str, **kwargs: object) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def request(method: str, path: str, **kwargs: object) -> httpx.Response:
    return asyncio.run(_request(method, path, **kwargs))


class FakeSelector:
    def __init__(self) -> None:
        self.max_pages = 6
        self.model = "fake-claude"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        self.calls.append(payload)
        return PageSelectionResult(
            pages_used=["index.md"],
            tool_trace=[],
            token_summary={
                "model": "fake-claude",
                "calls": 1,
                "input_tokens": 90,
                "output_tokens": 20,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 110,
                "per_call": [
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 90,
                        "output_tokens": 20,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 110,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 500,
                "selector_wall_time_ms": 550,
                "per_call": [{"call_number": 1, "duration_ms": 500, "stop_reason": "end_turn"}],
            },
        )


class FakeAnswerer:
    def __init__(self) -> None:
        self.model = "fake-claude"
        self.calls: list[dict[str, object]] = []

    def run(self, question: str, pages: list[dict[str, object]]) -> AnswerResult:
        self.calls.append({"question": question, "pages": pages})
        return AnswerResult(
            answer="F33 is mandatory for acrylamide per CHEMMON12.",
            citations=["index.md"],
            token_summary={
                "model": "fake-claude",
                "calls": 1,
                "input_tokens": 200,
                "output_tokens": 50,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 250,
                "per_call": [
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 200,
                        "output_tokens": 50,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 250,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 600,
                "answerer_wall_time_ms": 650,
                "per_call": [{"call_number": 1, "duration_ms": 600, "stop_reason": "end_turn"}],
            },
        )


class FakeBadAnswerer:
    def __init__(self) -> None:
        self.model = "fake-claude"

    def run(self, question: str, pages: list[dict[str, object]]) -> AnswerResult:
        raise ValueError("Could not extract answer from model response")


def setup_function() -> None:
    app_module.selector_runner = FakeSelector()
    app_module.answerer_runner = FakeAnswerer()


def test_health() -> None:
    response = request("GET", "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_index() -> None:
    response = request("GET", "/wiki/index")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_name"] == "index.md"
    assert "Wiki Index" in payload["title"]


def test_list_pages_empty_before_ingest() -> None:
    response = request("GET", "/wiki/pages")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 0
    assert payload["pages"] == []


def test_get_unknown_page_returns_404() -> None:
    response = request("GET", "/wiki/pages/not-a-real-page.md")
    assert response.status_code == 404


def test_ask_returns_answer_with_citations() -> None:
    response = request(
        "POST",
        "/wiki/ask",
        json={"question": "Do I need F33 for acrylamide?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "F33 is mandatory for acrylamide per CHEMMON12."
    assert payload["citations"] == ["index.md"]
    assert "index.md" in payload["pages_used"]
    assert payload["trace"]["selection_method"] == "service-owned llm page selector + answerer"
    assert payload["trace"]["selector"]["model"] == "fake-claude"
    assert payload["trace"]["answerer"]["model"] == "fake-claude"
    assert payload["trace"]["total"]["total_llm_calls"] == 2
    assert app_module.selector_runner.calls[0]["question"] == "Do I need F33 for acrylamide?"


def test_ask_requires_question() -> None:
    response = request("POST", "/wiki/ask", json={})
    assert response.status_code == 422


def test_ask_returns_503_on_answerer_error() -> None:
    app_module.answerer_runner = FakeBadAnswerer()
    response = request(
        "POST",
        "/wiki/ask",
        json={"question": "test question"},
    )
    assert response.status_code == 503


def test_openapi_exposes_ask_endpoint() -> None:
    response = request("GET", "/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "/wiki/ask" in payload["paths"]
    assert "AskRequest" in payload["components"]["schemas"]
    assert "AskResponse" in payload["components"]["schemas"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_app.py -v
```

Expected: FAIL because `app.py` still has FoodEx2 code.

- [ ] **Step 3: Rewrite app.py**

```python
from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .answerer import AnthropicChemMonAnswerer
from .page_selector import AnthropicWikiPageSelector
from .wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent
store = WikiStore(REPO_ROOT)
selector_runner: AnthropicWikiPageSelector | Any | None = None
answerer_runner: AnthropicChemMonAnswerer | Any | None = None
logger = logging.getLogger("wiki_api")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def get_selector_runner() -> AnthropicWikiPageSelector | Any:
    global selector_runner
    if selector_runner is None:
        selector_runner = AnthropicWikiPageSelector(store=store)
    return selector_runner


def get_answerer_runner() -> AnthropicChemMonAnswerer | Any:
    global answerer_runner
    if answerer_runner is None:
        answerer_runner = AnthropicChemMonAnswerer()
    return answerer_runner


class AskRequest(BaseModel):
    question: str = Field(description="The user's question about ChemMon reporting.")
    max_pages: int = Field(default=6, ge=1, le=10)


class PageSummary(BaseModel):
    page_name: str
    title: str
    summary: str
    sources: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    content: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[str]
    pages_used: list[str]
    pages: list[PageSummary]
    trace: dict[str, Any]


app = FastAPI(
    title="ChemMon Wiki API",
    version="0.1.0",
    description="Wiki-owned Q&A API for EFSA Chemical Monitoring reporting guidance.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/wiki/view", include_in_schema=False)
def wiki_viewer():
    return FileResponse(STATIC_DIR / "viewer.html", media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/wiki/index")
def get_index() -> dict[str, Any]:
    index = store.read_page("index.md")
    return {
        "page_name": index.name,
        "title": index.title,
        "summary": index.summary,
        "content": index.content,
    }


@app.get("/wiki/pages")
def list_pages() -> dict[str, Any]:
    pages = [
        {
            "page_name": page.name,
            "title": page.title,
            "summary": page.summary,
            "sources": page.sources,
            "related": page.related,
        }
        for page in store.catalog()
    ]
    return {"pages": pages, "count": len(pages)}


@app.get("/wiki/pages/{page_name}")
def get_page(page_name: str, include_content: bool = Query(default=True)) -> dict[str, Any]:
    try:
        page = store.read_page(page_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "page_name": page.name,
        "title": page.title,
        "summary": page.summary,
        "sources": page.sources,
        "related": page.related,
        "content": page.content if include_content else None,
    }


@app.post(
    "/wiki/ask",
    response_model=AskResponse,
    summary="Ask a question about ChemMon reporting",
    description=(
        "Send a natural language question about EFSA Chemical Monitoring reporting. "
        "The service selects relevant wiki pages and returns a grounded answer with citations."
    ),
)
def ask_question(request: AskRequest) -> AskResponse:
    request_started = time.perf_counter()
    logger.info(
        "ask_request %s",
        json.dumps({"question": request.question, "max_pages": request.max_pages}, ensure_ascii=False),
    )

    selector = get_selector_runner()
    if request.max_pages != selector.max_pages:
        selector.max_pages = request.max_pages

    try:
        selection_result = selector.run({"question": request.question})
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pages_raw = [store.read_page(page_name) for page_name in selection_result.pages_used]
    page_contents = [
        {"page_name": page.name, "content": store.clean_content_for_model(page)}
        for page in pages_raw
    ]

    answerer = get_answerer_runner()
    try:
        answer_result = answerer.run(question=request.question, pages=page_contents)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pages = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=store.clean_content_for_model(page),
        )
        for page in pages_raw
    ]

    response = AskResponse(
        answer=answer_result.answer,
        citations=answer_result.citations,
        pages_used=selection_result.pages_used,
        pages=pages,
        trace={
            "selection_method": "service-owned llm page selector + answerer",
            "selector": {
                "model": selector.model,
                "tool_trace": selection_result.tool_trace,
                "token_summary": selection_result.token_summary,
                "timing_summary": selection_result.timing_summary,
            },
            "answerer": {
                "model": answerer.model,
                "token_summary": answer_result.token_summary,
                "timing_summary": answer_result.timing_summary,
            },
            "total": {
                "request_wall_time_ms": int((time.perf_counter() - request_started) * 1000),
                "total_llm_calls": (
                    int(selection_result.token_summary["calls"])
                    + int(answer_result.token_summary["calls"])
                ),
                "total_tracked_tokens": (
                    int(selection_result.token_summary["total_tracked_tokens"])
                    + int(answer_result.token_summary["total_tracked_tokens"])
                ),
            },
        },
    )
    logger.info(
        "ask_response %s",
        json.dumps(
            {
                "question": request.question,
                "answer_length": len(response.answer),
                "citations": response.citations,
                "pages_used": response.pages_used,
                "total_tokens": response.trace["total"]["total_tracked_tokens"],
            },
            ensure_ascii=False,
        ),
    )
    return response
```

- [ ] **Step 4: Delete FoodEx2-specific files**

```bash
rm wiki_api/policy.py
rm tests/test_wiki_api.py
rm tests/test_librarian.py
```

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```

Expected: all tests in `test_wiki_store.py`, `test_page_selector.py`, `test_answerer.py`, and `test_app.py` PASS.

- [ ] **Step 6: Commit**

```bash
git add wiki_api/app.py tests/test_app.py
git add -u  # picks up deleted files
git commit -m "Replace FoodEx2 API with ChemMon Q&A endpoint"
```

---

### Task 6: Update viewer and requirements

**Files:**
- Modify: `wiki_api/static/viewer.html`
- Verify: `requirements.txt`

- [ ] **Step 1: Update viewer.html title**

In `wiki_api/static/viewer.html`, change the `<title>` tag from `FoodEx2 Wiki` to `ChemMon Wiki`. Also update any heading text that says "FoodEx2" to "ChemMon".

Search for "FoodEx2" in the file and replace all occurrences with "ChemMon".

- [ ] **Step 2: Verify requirements.txt**

Confirm `requirements.txt` contains:

```
fastapi>=0.104,<1.0
uvicorn>=0.23,<1.0
PyYAML>=6.0,<7.0
anthropic>=0.79,<1.0
pytest>=9.0,<10.0
python-dotenv>=1.0,<2.0
```

No changes needed — same dependencies.

- [ ] **Step 3: Run all tests one final time**

```bash
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add wiki_api/static/viewer.html
git commit -m "Update viewer branding to ChemMon"
```

---

### Task 7: Final verification and push

- [ ] **Step 1: Verify directory structure**

```bash
ls -la chemmon_docs/
ls -la raw/chemmon-guidance/
ls wiki_api/
ls tests/
```

Expected:
- `chemmon_docs/` has `.gitkeep`
- `raw/chemmon-guidance/` has `.gitkeep`
- `wiki_api/` has: `__init__.py`, `app.py`, `page_selector.py`, `answerer.py`, `wiki_store.py`, `static/`
- `tests/` has: `conftest.py`, `test_wiki_store.py`, `test_page_selector.py`, `test_answerer.py`, `test_app.py`

- [ ] **Step 2: Verify no FoodEx2 references remain in Python code**

```bash
grep -r "FoodEx2\|foodex2\|efsa-guidance\|librarian\|policy_pack\|solver\|CandidateHint\|SolveCandidate" wiki_api/ tests/ --include="*.py"
```

Expected: no matches.

- [ ] **Step 3: Run the service locally to verify**

```bash
. .venv/bin/activate
uvicorn wiki_api.app:app --port 8005 &
curl http://localhost:8005/health
curl http://localhost:8005/wiki/index
curl http://localhost:8005/wiki/pages
kill %1
```

Expected: health returns `{"status": "ok"}`, index returns the ChemMon index, pages returns empty list.

- [ ] **Step 4: Push to GitHub**

```bash
git push -u origin main
```
