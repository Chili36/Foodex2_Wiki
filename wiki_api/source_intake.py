from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
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
from .wiki_store import WikiStore


# max_tokens is a ceiling, not a prepaid charge, but raising it can increase cost
# by allowing more billed thinking/output tokens. Keep routine intake conservative;
# the larger ceiling is used only when thinking is explicitly enabled.
DEFAULT_SOURCE_INTAKE_MAX_TOKENS = 5000
DEFAULT_SOURCE_INTAKE_MAX_TOKENS_WITH_THINKING = 9000


class SourceIntakeError(RuntimeError):
    """Raised when the source-intake pass cannot produce a usable report."""


SOURCE_INTAKE_SYSTEM_PROMPT = """You are the FoodEx2 wiki source-intake reviewer.

Your job is to write a pre-ingest source impact report. This is a maintainer decision aid, not an operational wiki rule and not a final FoodEx2 coding answer.

Use the provided source text, source metadata, current wiki index, selected existing pages, ingest workflow, schema, recent log, and doctor report to decide what the source would add to the wiki.

Do not rewrite wiki pages. Do not invent source claims. Do not promote examples into rules. Be explicit about source tier, authority boundaries, overlap with existing pages, conflicts, risks, and what should or should not be ingested.

Return Markdown only with these sections:
1. Intake Verdict
2. Source Identity
3. Scope
4. Novel Contributions
5. Overlap With Existing Wiki
6. Conflicts Or Tension
7. Ingest Risks
8. Recommended Action
9. Candidate Test Cases
10. Open Questions
"""


@dataclass(frozen=True)
class SourceIntakeResult:
    report: str
    source_file: str
    token_summary: dict[str, Any]
    timing_summary: dict[str, Any]
    extraction_warnings: tuple[str, ...] = ()
    output_path: Path | None = None


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[TRUNCATED]"


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized or "source-intake"


def _pdf_text_appears_sparse(text: str) -> bool:
    raw_pages = text.split("\f")
    if text.endswith("\f"):
        # pdftotext terminates the final page with a form feed. Remove only the
        # resulting sentinel so empty segments for actual image-only pages remain.
        raw_pages.pop()
    pages = [_clean_text(raw_page) for raw_page in raw_pages]
    if not pages or not any(pages):
        return True
    total_chars = sum(len(page) for page in pages)
    empty_pages = sum(1 for page in pages if not page)
    if empty_pages / len(pages) > 0.25:
        return True
    average_chars = total_chars / len(pages)
    sparse_pages = sum(1 for page in pages if len(page) < 250)
    return average_chars < 700 and sparse_pages / len(pages) > 0.25


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _read_text_source(path: Path, *, max_chars: int) -> tuple[str, str, list[str]]:
    if path.suffix.lower() == ".pdf":
        try:
            completed = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            warning = (
                "[PDF text extraction unavailable. Provide --source-text-file with OCR or "
                "curated extraction for deeper intake analysis.]"
            )
            return warning, "PDF text extraction unavailable", [warning]
        text = completed.stdout.strip(" \t\r\n")
        if not _clean_text(text.replace("\f", "\n")):
            warning = (
                "[PDF text extraction returned no text. Provide --source-text-file with OCR or "
                "curated extraction for deeper intake analysis.]"
            )
            return warning, "PDF text extraction returned no text", [warning]
        if _pdf_text_appears_sparse(text):
            warning = (
                "[PDF text extraction appears sparse or incomplete. Provide --source-text-file "
                "with OCR or curated extraction before relying on this intake report.]"
            )
            sparse_text = _truncate(text, max_chars)
            return (
                f"{warning}\n\nExtracted sparse text:\n{sparse_text}",
                "PDF text extraction appears sparse; source-text-file recommended",
                [warning],
            )
        return (
            _truncate(text, max_chars),
            "source text extracted directly from PDF text layer",
            [],
        )

    try:
        return (
            _truncate(path.read_text(encoding="utf-8"), max_chars),
            "source text loaded directly from source file",
            [],
        )
    except UnicodeDecodeError:
        return (
            _truncate(path.read_text(encoding="latin-1"), max_chars),
            "source text loaded directly from source file with latin-1 fallback",
            [],
        )


def _resolve_pages(store: WikiStore, page_names: list[str]) -> list[str]:
    resolved: list[str] = []
    for page_name in page_names:
        normalized = store.resolve_page_reference(page_name)
        if normalized is None:
            raise FileNotFoundError(f"Unknown wiki page for source intake: {page_name}")
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved


def build_source_intake_payload(
    *,
    root: Path | str = ".",
    source_file: Path | str,
    source_text_file: Path | str | None = None,
    source_tier: str = "expert_guidance",
    focus: str = "",
    page_names: list[str] | None = None,
    max_source_chars: int = 40000,
    max_page_chars: int = 10000,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    store = WikiStore(root_path)
    source_path = Path(source_file)
    if not source_path.is_absolute():
        source_path = root_path / source_path
    source_path = source_path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    if source_text_file is not None:
        text_path = Path(source_text_file)
        if not text_path.is_absolute():
            text_path = root_path / text_path
        source_text = _truncate(text_path.read_text(encoding="utf-8"), max_source_chars)
        extraction_note = f"source text loaded from {text_path}"
        extraction_warnings: list[str] = []
    else:
        source_text, extraction_note, extraction_warnings = _read_text_source(
            source_path,
            max_chars=max_source_chars,
        )

    selected_pages = _resolve_pages(store, page_names or [])
    return {
        "focus": focus,
        "source": {
            "file": str(
                source_path.relative_to(root_path)
                if source_path.is_relative_to(root_path)
                else source_path
            ),
            "name": source_path.name,
            "suffix": source_path.suffix.lower(),
            "source_tier": source_tier,
            "extraction_note": extraction_note,
            "extraction_warnings": extraction_warnings,
            "source_text": source_text,
        },
        "doctor_report": run_doctor(root_path).as_dict(),
        "wiki_index": store.read_page("index.md").content,
        "schema": store.read_page("SCHEMA.md").content,
        "ingest_workflow": store.read_page("INGEST_WORKFLOW.md").content,
        "recent_log": _truncate(store.read_page("log.md").content, 12000),
        "selected_existing_pages": [
            {
                "page_name": page_name,
                "title": store.read_page(page_name).title,
                "summary": store.read_page(page_name).summary,
                "content": _truncate(store.read_page(page_name).content, max_page_chars),
            }
            for page_name in selected_pages
        ],
    }


class AnthropicSourceIntakeReviewer:
    def __init__(
        self,
        *,
        client: AnthropicClientProtocol | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        thinking_enabled: bool | None = None,
    ):
        self.model = model or _resolve_model(
            "WIKI_INTAKE_MODEL",
            "WIKI_LINT_MODEL",
            "WIKI_LIBRARIAN_MODEL",
            default="claude-sonnet-4-6",
        )
        self.client = client or build_messages_client(self.model)
        self.thinking_enabled = (
            _env_bool("WIKI_INTAKE_THINKING", default=False)
            if thinking_enabled is None
            else thinking_enabled
        )
        if max_tokens is not None:
            self.max_tokens = max_tokens
        elif self.thinking_enabled:
            self.max_tokens = DEFAULT_SOURCE_INTAKE_MAX_TOKENS_WITH_THINKING
        else:
            self.max_tokens = DEFAULT_SOURCE_INTAKE_MAX_TOKENS

    def run(self, payload: dict[str, Any]) -> SourceIntakeResult:
        started = time.perf_counter()
        message = {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        }
        llm_started = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SOURCE_INTAKE_SYSTEM_PROMPT,
            messages=[message],
            **_anthropic_thinking_args(self.thinking_enabled),
        )
        stop_reason = _get_block_value(response, "stop_reason")
        report = _response_text(_get_block_value(response, "content", []))
        if not report:
            raise SourceIntakeError(self._empty_report_message(stop_reason))
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
        return SourceIntakeResult(
            report=report,
            source_file=str(payload.get("source", {}).get("file", "")),
            token_summary=token_summary,
            timing_summary={
                **_aggregate_timing(timing),
                "source_intake_wall_time_ms": int((time.perf_counter() - started) * 1000),
            },
            extraction_warnings=tuple(
                str(warning)
                for warning in payload.get("source", {}).get("extraction_warnings", [])
                if str(warning).strip()
            ),
        )

    def _empty_report_message(self, stop_reason: Any) -> str:
        base = (
            "Source intake produced no report text "
            f"(stop_reason={stop_reason!r}, max_tokens={self.max_tokens})."
        )
        if stop_reason == "max_tokens":
            if self.thinking_enabled:
                return (
                    base
                    + " The output budget was likely consumed entirely by thinking"
                    " before any report text was emitted. Raise --max-tokens"
                    " or pass --no-thinking (or set WIKI_INTAKE_THINKING=0)"
                    " and retry."
                )
            return base + " Raise --max-tokens and retry."
        return base


def _default_output_path(root: Path, source_file: str) -> Path:
    stem = _slug(Path(source_file).stem)
    return root / "reports" / "source-intake" / f"{stem}.md"


def _render_report(result: SourceIntakeResult) -> str:
    metadata = [
        "---",
        f'generated_at: "{datetime.now().isoformat(timespec="seconds")}"',
        f'model: "{result.token_summary.get("model", "")}"',
        f'thinking_enabled: {str(result.token_summary.get("thinking_enabled", False)).lower()}',
        f'source_file: "{result.source_file}"',
        "---",
        "",
    ]
    warnings = []
    if result.extraction_warnings:
        warnings = [
            "## Extraction Warnings",
            "",
            *(f"- {warning}" for warning in result.extraction_warnings),
            "",
        ]
    return "\n".join([*metadata, *warnings]) + result.report.strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an LLM-assisted source impact report.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--source-file", required=True, help="Source document path.")
    parser.add_argument(
        "--source-text-file",
        default=None,
        help="Optional extracted/OCR text file to use instead of direct source extraction.",
    )
    parser.add_argument(
        "--source-tier",
        default="expert_guidance",
        choices=["authoritative_rule", "expert_guidance", "local_policy", "diagnostic"],
    )
    parser.add_argument("--focus", default="", help="Optional intake focus.")
    parser.add_argument(
        "--page",
        action="append",
        default=[],
        help="Existing wiki page likely affected by the source. May be repeated.",
    )
    parser.add_argument("--model", default=None, help="Override model. Defaults to WIKI_INTAKE_MODEL.")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help=(
            "Output token ceiling. Defaults to "
            f"{DEFAULT_SOURCE_INTAKE_MAX_TOKENS_WITH_THINKING} when thinking is "
            f"enabled, otherwise {DEFAULT_SOURCE_INTAKE_MAX_TOKENS}."
        ),
    )
    parser.add_argument("--max-source-chars", type=int, default=40000)
    parser.add_argument("--max-page-chars", type=int, default=10000)
    parser.add_argument(
        "--thinking",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable Anthropic adaptive thinking. Defaults to WIKI_INTAKE_THINKING, or off.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Report path. Defaults to reports/source-intake/<source-stem>.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the source-intake payload without calling the LLM.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    payload = build_source_intake_payload(
        root=root,
        source_file=args.source_file,
        source_text_file=args.source_text_file,
        source_tier=args.source_tier,
        focus=args.focus,
        page_names=args.page,
        max_source_chars=args.max_source_chars,
        max_page_chars=args.max_page_chars,
    )

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    try:
        result = AnthropicSourceIntakeReviewer(
            model=args.model,
            max_tokens=args.max_tokens,
            thinking_enabled=args.thinking,
        ).run(payload)
    except SourceIntakeError as exc:
        print(f"Source intake failed: {exc}", file=sys.stderr)
        return 1
    output_path = Path(args.output) if args.output else _default_output_path(root, args.source_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_report(result), encoding="utf-8")
    print(f"Wrote source impact report: {output_path}")
    print(
        json.dumps(
            {
                "source_file": result.source_file,
                "token_summary": result.token_summary,
                "timing_summary": result.timing_summary,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
