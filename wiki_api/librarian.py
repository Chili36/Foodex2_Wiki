from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import time
from typing import Any, Protocol

from anthropic import Anthropic
from dotenv import load_dotenv

from .wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


TOOLS = [
    {
        "name": "read_wiki_pages",
        "description": (
            "Read one or more non-index pages from the local FoodEx2 wiki by filename. "
            "Use this to batch the page reads you need after reviewing the provided index."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "page_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Wiki filenames to read, for example "
                        "['base-term-selection.md', 'packaging-facets.md']"
                    ),
                }
            },
            "required": ["page_names"],
        },
    }
]

SYSTEM_PROMPT = """You are the FoodEx2 wiki librarian.

Your only job is to read the local FoodEx2 wiki and return the smallest useful knowledge packet for the current coding case.

Rules:
- The full catalog from `index.md` is already provided in the user message.
- Use that catalog first to decide which pages matter.
- Do not request `index.md` again unless the provided catalog is clearly insufficient.
- When you need more detail, request multiple pages in one `read_wiki_pages` call whenever possible.
- Then choose only the wiki pages relevant to the current case.
- Open only the pages needed.
- Prefer guidance pages for food-type and base-term questions.
- Prefer validation pages for facet legality and code construction.
- Prefer domain pages only when the case indicates that domain.
- Use maintenance pages only if the case may depend on annual changes.
- Never make the final FoodEx2 coding decision.
- Never answer from FoodEx2 memory if the wiki can answer it.
- You may read at most 6 wiki pages total, including `index.md`.
- If the wiki is insufficient, return that explicitly in `wiki_gaps`.

Return JSON only with this structure:
{
  "pages_used": ["index.md"],
  "query_classification": {
    "food_type": "raw|derivative|composite|unclear",
    "domain": "general_food|chemmon|vmpr|additives|acrylamide|feed|unknown",
    "signals": ["..."]
  },
  "candidate_focus": {
    "promising_codes": ["..."],
    "rejected_patterns": ["..."]
  },
  "policy_pack": {
    "base_term_rules": ["..."],
    "facet_rules": ["..."],
    "validation_rules": ["..."],
    "domain_rules": ["..."],
    "construction_rules": ["..."],
    "open_questions": ["..."],
    "wiki_gaps": ["..."]
  }
}
"""


class AnthropicMessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClientProtocol(Protocol):
    @property
    def messages(self) -> AnthropicMessagesClient: ...


@dataclass(frozen=True)
class LibrarianResult:
    data: dict[str, Any]
    tool_trace: list[dict[str, Any]]
    token_summary: dict[str, Any]
    timing_summary: dict[str, Any]


def _get_block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _to_message_blocks(content_blocks: list[Any]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for block in content_blocks:
        block_type = _get_block_value(block, "type")
        if block_type == "text":
            serialized.append({"type": "text", "text": _get_block_value(block, "text", "")})
        elif block_type == "tool_use":
            serialized.append(
                {
                    "type": "tool_use",
                    "id": _get_block_value(block, "id"),
                    "name": _get_block_value(block, "name"),
                    "input": _get_block_value(block, "input", {}),
                }
            )
    return serialized


def _response_text(content_blocks: list[Any]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        if _get_block_value(block, "type") == "text":
            parts.append(_get_block_value(block, "text", ""))
    return "".join(parts).strip()


def _extract_json_payload(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Empty final response from librarian")
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
        candidate = text[brace_start : brace_end + 1]
        return json.loads(candidate)
    raise ValueError("Could not extract JSON object from librarian response")


def _usage_dict(usage: Any, *, stop_reason: str | None) -> dict[str, int | str | None]:
    input_tokens = int(_get_block_value(usage, "input_tokens", 0) or 0)
    output_tokens = int(_get_block_value(usage, "output_tokens", 0) or 0)
    cache_creation_input_tokens = int(
        _get_block_value(usage, "cache_creation_input_tokens", 0) or 0
    )
    cache_read_input_tokens = int(
        _get_block_value(usage, "cache_read_input_tokens", 0) or 0
    )
    return {
        "stop_reason": stop_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "total_tracked_tokens": (
            input_tokens
            + output_tokens
            + cache_creation_input_tokens
            + cache_read_input_tokens
        ),
    }


def _aggregate_usage(usages: list[dict[str, int | str | None]], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "calls": len(usages),
        "input_tokens": sum(int(item["input_tokens"]) for item in usages),
        "output_tokens": sum(int(item["output_tokens"]) for item in usages),
        "cache_creation_input_tokens": sum(
            int(item["cache_creation_input_tokens"]) for item in usages
        ),
        "cache_read_input_tokens": sum(
            int(item["cache_read_input_tokens"]) for item in usages
        ),
        "total_tracked_tokens": sum(int(item["total_tracked_tokens"]) for item in usages),
        "per_call": usages,
    }


def _aggregate_timing(timings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "calls": len(timings),
        "llm_time_ms": sum(int(item["duration_ms"]) for item in timings),
        "per_call": timings,
    }


def build_anthropic_client() -> AnthropicClientProtocol:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return Anthropic(api_key=api_key)


class AnthropicWikiLibrarian:
    def __init__(
        self,
        *,
        store: WikiStore,
        client: AnthropicClientProtocol | None = None,
        model: str | None = None,
        max_pages: int = 6,
        max_tokens: int = 4000,
    ):
        self.store = store
        self.client = client or build_anthropic_client()
        self.model = model or os.getenv("WIKI_LIBRARIAN_MODEL", "claude-3-7-sonnet-latest")
        self.max_pages = max_pages
        self.max_tokens = max_tokens

    def _batch_read_pages(
        self,
        requested_page_names: list[str],
        *,
        pages_read: list[str],
        tool_trace: list[dict[str, Any]],
    ) -> str:
        pages: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        max_followup_pages = max(self.max_pages - 1, 0)
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
                skipped.append(
                    {
                        "page_name": page_name,
                        "reason": "page_limit_exceeded",
                        "limit": self.max_pages,
                    }
                )
                continue

            try:
                page = self.store.read_page(page_name)
                normalized_name = self.store.normalize_page_name(page_name)
                if normalized_name in pages_read:
                    skipped.append(
                        {"page_name": normalized_name, "reason": "already_read_in_conversation"}
                    )
                    continue
                pages_read.append(normalized_name)
                tool_trace.append(
                    {
                        "page_name": normalized_name,
                        "order": len(tool_trace) + 1,
                        "chars": len(page.content),
                        "synthetic": False,
                    }
                )
                pages.append({"page_name": normalized_name, "content": page.content})
            except Exception as exc:
                errors.append(
                    {
                        "page_name": page_name,
                        "reason": "read_failed",
                        "message": str(exc),
                    }
                )
                tool_trace.append(
                    {
                        "page_name": page_name,
                        "order": len(tool_trace) + 1,
                        "chars": len(str(exc)),
                        "synthetic": True,
                    }
                )

        return json.dumps(
            {
                "pages": pages,
                "skipped": skipped,
                "errors": errors,
            },
            ensure_ascii=False,
        )

    def run(self, payload: dict[str, Any]) -> LibrarianResult:
        librarian_started = time.perf_counter()
        index_content = self.store.read_page("index.md").content
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case": payload,
                        "wiki_index": index_content,
                    },
                    ensure_ascii=False,
                ),
            }
        ]
        pages_read: list[str] = []
        tool_trace: list[dict[str, Any]] = []
        usage_trace: list[dict[str, int | str | None]] = []
        timing_trace: list[dict[str, Any]] = []

        while True:
            llm_started = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            llm_duration_ms = int((time.perf_counter() - llm_started) * 1000)
            timing_trace.append(
                {
                    "call_number": len(timing_trace) + 1,
                    "duration_ms": llm_duration_ms,
                    "stop_reason": _get_block_value(response, "stop_reason"),
                }
            )
            usage_trace.append(
                _usage_dict(
                    _get_block_value(response, "usage"),
                    stop_reason=_get_block_value(response, "stop_reason"),
                )
            )
            content = _get_block_value(response, "content", [])
            tool_uses = [block for block in content if _get_block_value(block, "type") == "tool_use"]
            if not tool_uses:
                final_text = _response_text(content)
                data = _extract_json_payload(final_text)
                normalized_pages = [self.store.normalize_page_name(name) for name in pages_read]
                data["pages_used"] = list(dict.fromkeys(["index.md", *normalized_pages]))
                return LibrarianResult(
                    data=data,
                    tool_trace=tool_trace,
                    token_summary=_aggregate_usage(usage_trace, self.model),
                    timing_summary={
                        **_aggregate_timing(timing_trace),
                        "librarian_wall_time_ms": int(
                            (time.perf_counter() - librarian_started) * 1000
                        ),
                    },
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": _to_message_blocks(content),
                }
            )

            tool_results: list[dict[str, Any]] = []
            for block in tool_uses:
                page_names = _get_block_value(block, "input", {}).get("page_names", [])
                if not isinstance(page_names, list):
                    page_names = [page_names]
                tool_output = self._batch_read_pages(
                    [str(name) for name in page_names],
                    pages_read=pages_read,
                    tool_trace=tool_trace,
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": _get_block_value(block, "id"),
                        "content": tool_output,
                    }
                )

            messages.append({"role": "user", "content": tool_results})
