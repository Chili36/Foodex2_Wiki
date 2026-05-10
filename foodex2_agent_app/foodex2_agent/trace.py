from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import ToolCallRecord
from .settings import Settings


LIST_KEYS = ("terms", "results", "items", "facets", "pages", "parents", "children")
KEEP_KEYS = {
    "code",
    "name",
    "type",
    "termType",
    "term_type",
    "scopeNote",
    "detail_level",
    "matchedIn",
    "facet_group",
    "facetType",
    "groupId",
    "descriptor",
    "descriptorCode",
    "facetCode",
    "valid",
    "warnings",
    "hardWarnings",
    "softWarnings",
    "infoWarnings",
    "baseTerm",
    "cleanedCode",
    "interpretedDescription",
    "page_name",
    "title",
    "content",
}


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]


class RunLogger:
    def __init__(self, settings: Settings, run_id: str):
        base = Path(settings.run_log_dir)
        if not base.is_absolute():
            base = Path(__file__).resolve().parents[1] / base
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / f"{run_id}.jsonl"

    def write(self, event: dict[str, Any]) -> None:
        payload = {"ts": datetime.now(timezone.utc).isoformat(), **event}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def compact_for_model(result: Any, settings: Settings) -> Any:
    return compact_value(
        result,
        max_items=settings.tool_model_max_items,
        max_chars=settings.tool_string_max_chars,
    )[0]


def make_trace_record(
    *,
    name: str,
    arguments: dict[str, Any],
    result: Any,
    settings: Settings,
    log_ref: str,
) -> ToolCallRecord:
    compact, truncated, count = compact_value(
        result,
        max_items=settings.tool_trace_max_items,
        max_chars=settings.tool_string_max_chars,
    )
    return ToolCallRecord(
        name=name,
        arguments=arguments,
        result=compact,
        resultCount=count,
        truncated=truncated,
        logRef=log_ref,
    )


def compact_value(value: Any, *, max_items: int, max_chars: int) -> tuple[Any, bool, int | None]:
    if isinstance(value, list):
        compact_items = []
        truncated = len(value) > max_items
        for item in value[:max_items]:
            compact_items.append(compact_item(item, max_chars=max_chars))
        if truncated:
            compact_items.append({"_truncated": f"{len(value) - max_items} more item(s) omitted"})
        return compact_items, truncated, len(value)

    if isinstance(value, dict):
        for key in LIST_KEYS:
            items = value.get(key)
            if isinstance(items, list):
                compact_dict = dict(value)
                compact_items = [compact_item(item, max_chars=max_chars) for item in items[:max_items]]
                truncated = len(items) > max_items
                if truncated:
                    compact_items.append({"_truncated": f"{len(items) - max_items} more item(s) omitted"})
                compact_dict[key] = compact_items
                compact_dict["_resultCount"] = len(items)
                compact_dict["_truncated"] = truncated
                return _compact_scalars(compact_dict, max_chars=max_chars), truncated, len(items)
        return _compact_scalars(value, max_chars=max_chars), False, None

    return _compact_scalar(value, max_chars=max_chars), False, None


def compact_item(item: Any, *, max_chars: int) -> Any:
    if not isinstance(item, dict):
        return _compact_scalar(item, max_chars=max_chars)

    kept: dict[str, Any] = {}
    for key in KEEP_KEYS:
        if key in item:
            kept[key] = _compact_scalar(item[key], max_chars=max_chars)

    if kept:
        return kept
    return _compact_scalars(item, max_chars=max_chars)


def _compact_scalars(value: dict[str, Any], *, max_chars: int) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            compact[key] = _compact_scalars(item, max_chars=max_chars)
        elif isinstance(item, list):
            compact[key] = [_compact_scalar(child, max_chars=max_chars) for child in item[:5]]
            if len(item) > 5:
                compact[key].append({"_truncated": f"{len(item) - 5} more item(s) omitted"})
        else:
            compact[key] = _compact_scalar(item, max_chars=max_chars)
    return compact


def _compact_scalar(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str) and len(value) > max_chars:
        return value[: max_chars - 1].rstrip() + "…"
    return value
