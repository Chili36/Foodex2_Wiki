from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from typing import Any

from .doctor import run_doctor
from .librarian import (
    AnthropicClientProtocol,
    _aggregate_timing,
    _aggregate_usage,
    _anthropic_thinking_args,
    _env_bool,
    _get_block_value,
    _resolve_model,
    _response_text,
    _usage_dict,
    build_messages_client,
)
from .wiki_store import (
    PROMPT_CONTEXT_OMITTED_SECTIONS,
    PROMPT_CONTEXT_PAGE_CATEGORIES,
    WikiPage,
    WikiStore,
)


DEFAULT_LINT_PAGES = [
    "index.md",
    "RUNTIME_RULES.md",
    "policy-contract.md",
    "SCHEMA.md",
    "MAINTENANCE_WORKFLOW.md",
]

# max_tokens is a ceiling, not a prepaid charge, but raising it can increase cost
# by allowing more billed thinking/output tokens. Keep routine lint conservative;
# the larger ceiling is used only when thinking is explicitly enabled.
DEFAULT_LINT_MAX_TOKENS = 4000
DEFAULT_LINT_MAX_TOKENS_WITH_THINKING = 8000


class WikiLintError(RuntimeError):
    """Raised when the lint pass cannot produce a usable report."""


LLM_LINT_SYSTEM_PROMPT = """You are the FoodEx2 wiki lint reviewer.

Your job is to review the provided wiki context for semantic and maintenance risks. This is a supervised maintenance pass: produce a report only. Do not rewrite pages, do not invent source claims, and do not make final FoodEx2 coding decisions.

Focus on:
- contradictions between pages
- stale or misleading index summaries
- missing routing signals for domain overlays
- pages that are too broad or too narrow for reliable retrieval
- claims that read like binding rules but are only examples
- examples that may be overgeneralized by a downstream model
- missing source traceability or weak citations
- prompt-context risks, especially where runtime projection omits or includes sections
- places where the deterministic wiki doctor cannot judge semantic correctness

Prioritize findings by severity:
- P1: likely to cause wrong FoodEx2 coding or invalid reporting
- P2: likely to cause retrieval mistakes, confusing prompt context, or brittle maintenance
- P3: cleanup, clarity, or traceability improvement

Return Markdown only with these sections:
1. Verdict
2. Findings
3. Suggested Follow-ups
4. Notes On Non-Issues

Every finding must name the page and quote or paraphrase the smallest relevant text. If there are no material findings, say so clearly.
"""


@dataclass(frozen=True)
class WikiLintResult:
    report: str
    pages_linted: list[str]
    token_summary: dict[str, Any]
    timing_summary: dict[str, Any]
    output_path: Path | None = None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED]"


def _resolve_pages(store: WikiStore, page_names: list[str], *, all_pages: bool) -> list[str]:
    if all_pages:
        return sorted(store.allowed_page_names())
    selected = page_names or DEFAULT_LINT_PAGES
    resolved: list[str] = []
    for page_name in selected:
        normalized = store.resolve_page_reference(page_name)
        if normalized is None:
            raise FileNotFoundError(f"Unknown wiki page for LLM lint: {page_name}")
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def _page_lint_payload(store: WikiStore, page: WikiPage, *, max_page_chars: int) -> dict[str, Any]:
    category = store.page_category(page.name)
    return {
        "page_name": page.name,
        "title": page.title,
        "category": category,
        "summary": page.summary,
        "sources": page.sources,
        "related": page.related,
        "backlinks": store.page_backlinks(page.name)["backlinks"],
        "prompt_facing": category in PROMPT_CONTEXT_PAGE_CATEGORIES,
        "prompt_projection": store.prompt_content_for_context_pack(page),
        "raw_content": _truncate(page.content, max_page_chars),
    }


def build_lint_payload(
    *,
    root: Path | str = ".",
    page_names: list[str] | None = None,
    all_pages: bool = False,
    focus: str | None = None,
    max_page_chars: int = 12000,
) -> dict[str, Any]:
    store = WikiStore(root)
    selected_pages = _resolve_pages(store, page_names or [], all_pages=all_pages)
    doctor_report = run_doctor(root)
    graph = store.graph_data()
    log_page = store.read_page("log.md")

    return {
        "focus": focus or "",
        "doctor_report": doctor_report.as_dict(),
        "selected_pages": selected_pages,
        "prompt_projection_policy": {
            "prompt_facing_categories": sorted(PROMPT_CONTEXT_PAGE_CATEGORIES),
            "omitted_sections": sorted(PROMPT_CONTEXT_OMITTED_SECTIONS),
        },
        "graph_summary": graph["summary"],
        "wiki_index": store.read_page("index.md").content,
        "recent_log": _truncate(log_page.content, 12000),
        "pages": [
            _page_lint_payload(
                store,
                store.read_page(page_name),
                max_page_chars=max_page_chars,
            )
            for page_name in selected_pages
        ],
    }


class AnthropicWikiLinter:
    def __init__(
        self,
        *,
        client: AnthropicClientProtocol | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        thinking_enabled: bool | None = None,
    ):
        self.model = model or _resolve_model(
            "WIKI_LINT_MODEL",
            "WIKI_LIBRARIAN_MODEL",
            default="claude-sonnet-4-6",
        )
        self.client = client or build_messages_client(self.model)
        self.thinking_enabled = (
            _env_bool("WIKI_LINT_THINKING", default=False)
            if thinking_enabled is None
            else thinking_enabled
        )
        if max_tokens is not None:
            self.max_tokens = max_tokens
        elif self.thinking_enabled:
            self.max_tokens = DEFAULT_LINT_MAX_TOKENS_WITH_THINKING
        else:
            self.max_tokens = DEFAULT_LINT_MAX_TOKENS

    def run(self, payload: dict[str, Any]) -> WikiLintResult:
        started = time.perf_counter()
        message = {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        }
        llm_started = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=LLM_LINT_SYSTEM_PROMPT,
            messages=[message],
            **_anthropic_thinking_args(self.thinking_enabled),
        )
        stop_reason = _get_block_value(response, "stop_reason")
        report = _response_text(_get_block_value(response, "content", []))
        if not report:
            raise WikiLintError(self._empty_report_message(stop_reason))
        timing = [
            {
                "call_number": 1,
                "duration_ms": int((time.perf_counter() - llm_started) * 1000),
                "stop_reason": stop_reason,
            }
        ]
        token_summary = _aggregate_usage(
            [
                _usage_dict(
                    _get_block_value(response, "usage"),
                    stop_reason=stop_reason,
                )
            ],
            self.model,
        )
        token_summary["thinking_enabled"] = self.thinking_enabled
        return WikiLintResult(
            report=report,
            pages_linted=list(payload.get("selected_pages", [])),
            token_summary=token_summary,
            timing_summary={
                **_aggregate_timing(timing),
                "lint_wall_time_ms": int((time.perf_counter() - started) * 1000),
            },
        )

    def _empty_report_message(self, stop_reason: Any) -> str:
        base = (
            "LLM lint produced no report text "
            f"(stop_reason={stop_reason!r}, max_tokens={self.max_tokens})."
        )
        if stop_reason == "max_tokens":
            if self.thinking_enabled:
                return (
                    base
                    + " The output budget was likely consumed entirely by thinking"
                    " before any report text was emitted. Raise --max-tokens"
                    " or pass --no-thinking (or set WIKI_LINT_THINKING=0)"
                    " and retry."
                )
            return base + " Raise --max-tokens and retry."
        return base


def _default_output_path(root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return root / "reports" / f"wiki-lint-{timestamp}.md"


def _render_report(result: WikiLintResult) -> str:
    metadata = [
        "---",
        f'generated_at: "{datetime.now().isoformat(timespec="seconds")}"',
        f'model: "{result.token_summary.get("model", "")}"',
        "pages_linted:",
        *[f"  - {page_name}" for page_name in result.pages_linted],
        "---",
        "",
    ]
    return "\n".join(metadata) + result.report.strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a supervised LLM lint pass over wiki pages.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument(
        "--page",
        action="append",
        default=[],
        help="Wiki page to lint. May be repeated. Defaults to core control pages.",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Lint all served wiki pages. This can use significantly more tokens.",
    )
    parser.add_argument("--focus", default="", help="Optional review focus, e.g. 'F09 examples'.")
    parser.add_argument("--model", default=None, help="Override model. Defaults to WIKI_LINT_MODEL.")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help=(
            "Output token ceiling. Defaults to "
            f"{DEFAULT_LINT_MAX_TOKENS_WITH_THINKING} when thinking is enabled, "
            f"otherwise {DEFAULT_LINT_MAX_TOKENS}."
        ),
    )
    parser.add_argument("--max-page-chars", type=int, default=12000)
    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable Anthropic adaptive thinking. Defaults to WIKI_LINT_THINKING, or off.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Report path. Defaults to reports/wiki-lint-<timestamp>.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the lint payload without calling the LLM.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    payload = build_lint_payload(
        root=root,
        page_names=args.page,
        all_pages=args.all_pages,
        focus=args.focus,
        max_page_chars=args.max_page_chars,
    )

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    try:
        result = AnthropicWikiLinter(
            model=args.model,
            max_tokens=args.max_tokens,
            thinking_enabled=args.thinking,
        ).run(payload)
    except WikiLintError as exc:
        print(f"LLM lint failed: {exc}", file=sys.stderr)
        return 1
    output_path = Path(args.output) if args.output else _default_output_path(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_report(result), encoding="utf-8")
    print(f"Wrote wiki lint report: {output_path}")
    print(
        json.dumps(
            {
                "pages_linted": result.pages_linted,
                "token_summary": result.token_summary,
                "timing_summary": result.timing_summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
