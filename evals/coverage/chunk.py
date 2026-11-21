"""Deterministically chunk authoritative sources with stable IDs and page refs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from evals.coverage.coverage_index import (
    DEFAULT_MANIFEST,
    REPO_ROOT,
    load_manifest,
    pdf_pages,
    source_local_path,
)


def _split_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        units = (
            [paragraph]
            if len(paragraph) <= max_chars
            else [paragraph[i : i + max_chars] for i in range(0, len(paragraph), max_chars)]
        )
        for unit in units:
            candidate = f"{current}\n\n{unit}".strip() if current else unit
            if current and len(candidate) > max_chars:
                parts.append(current)
                current = unit
            else:
                current = candidate
    if current:
        parts.append(current)
    return parts


def _source_units(source: dict[str, Any], max_chars: int) -> list[dict[str, Any]]:
    path = source_local_path(source)
    units: list[dict[str, Any]] = []
    if path.suffix.lower() == ".pdf":
        for page_number, page_text in pdf_pages(path):
            for part_number, text in enumerate(_split_text(page_text, max_chars), start=1):
                units.append(
                    {
                        "page_start": page_number,
                        "page_end": page_number,
                        "part": part_number,
                        "text": text,
                    }
                )
        return units

    content = path.read_text(encoding="utf-8")
    section_number = 0
    for section in re.split(r"(?m)(?=^#{1,6} )", content):
        section = section.strip()
        if not section:
            continue
        section_number += 1
        heading = section.splitlines()[0].lstrip("# ").strip() or f"section-{section_number}"
        for part_number, text in enumerate(_split_text(section, max_chars), start=1):
            units.append(
                {
                    "section": heading,
                    "section_number": section_number,
                    "part": part_number,
                    "text": text,
                }
            )
    return units


def chunk_sources(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    max_chars: int = 6000,
    source_ids: set[str] | None = None,
) -> dict[str, Any]:
    if max_chars < 500:
        raise ValueError("max_chars must be at least 500")
    sources = load_manifest(manifest_path)
    if source_ids:
        known = {str(source["id"]) for source in sources}
        unknown = source_ids - known
        if unknown:
            raise ValueError(f"unknown source ids: {sorted(unknown)}")
        sources = [source for source in sources if source["id"] in source_ids]
    chunks: list[dict[str, Any]] = []
    for source in sources:
        for unit in _source_units(source, max_chars):
            content_hash = hashlib.sha256(unit["text"].encode("utf-8")).hexdigest()
            if "page_start" in unit:
                location = f"p{unit['page_start']:04d}"
            else:
                location = f"s{unit['section_number']:04d}"
            chunk_id = f"{source['id']}:{location}:{unit['part']:02d}"
            chunks.append(
                {
                    "source_id": source["id"],
                    "source_title": source.get("title"),
                    "source_version": source.get("version"),
                    "source_sha256": source.get("sha256"),
                    "source_path": source.get("path"),
                    "chunk_id": chunk_id,
                    "content_sha256": content_hash,
                    **unit,
                }
            )
    resolved_manifest = manifest_path.resolve()
    manifest_label = (
        str(resolved_manifest.relative_to(REPO_ROOT))
        if resolved_manifest.is_relative_to(REPO_ROOT)
        else str(resolved_manifest)
    )
    return {
        "version": 1,
        "manifest": manifest_label,
        "max_chars": max_chars,
        "source_count": len(sources),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument("--source-id", action="append", dest="source_ids")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = chunk_sources(
        args.manifest.resolve(),
        max_chars=args.max_chars,
        source_ids=set(args.source_ids or []) or None,
    )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
