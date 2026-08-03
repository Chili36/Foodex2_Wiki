"""Diff source revisions and flag wiki pages and witness cases for re-review."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from evals.coverage.coverage_index import (
    REPO_ROOT,
    citation_pages,
    iter_cases,
    load_manifest,
    pdf_pages,
    source_local_path,
)


def _page_hashes(source: dict[str, Any]) -> dict[int, str]:
    path = source_local_path(source)
    if path.suffix.lower() != ".pdf":
        text = path.read_text(encoding="utf-8")
        return {1: hashlib.sha256(text.encode("utf-8")).hexdigest()}
    return {
        page: hashlib.sha256(text.encode("utf-8")).hexdigest()
        for page, text in pdf_pages(path)
    }


def _reference_is_impacted(reference: str, source: dict[str, Any], changed_pages: set[int]) -> bool:
    pages = citation_pages(reference, source)
    if pages is None:
        return False
    return not pages or bool(pages & changed_pages)


def _wiki_references() -> list[dict[str, str]]:
    references = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if any(part in {".git", ".venv", "reports", "foodex2_docs"} for part in path.parts):
            continue
        references.append(
            {
                "page": str(path.relative_to(REPO_ROOT)),
                "reference": path.read_text(encoding="utf-8"),
            }
        )
    return references


def compare_manifests(
    old_manifest: Path,
    new_manifest: Path,
    *,
    source_ids: set[str] | None = None,
) -> dict[str, Any]:
    old_sources = {source["id"]: source for source in load_manifest(old_manifest)}
    new_sources = {source["id"]: source for source in load_manifest(new_manifest)}
    selected = source_ids or (set(old_sources) | set(new_sources))
    unknown = selected - (set(old_sources) | set(new_sources))
    if unknown:
        raise ValueError(f"unknown source ids: {sorted(unknown)}")
    witness_cases = list(iter_cases(REPO_ROOT))
    wiki_references = _wiki_references()
    changed_sources = []
    impacted_wiki: dict[str, set[str]] = {}
    impacted_cases: dict[str, dict[str, Any]] = {}
    for source_id in sorted(selected):
        old = old_sources.get(source_id)
        new = new_sources.get(source_id)
        if old is None or new is None:
            changed_pages = set(_page_hashes(old or new))
            status = "added" if old is None else "removed"
        elif old.get("sha256") == new.get("sha256"):
            continue
        else:
            old_pages = _page_hashes(old)
            new_pages = _page_hashes(new)
            changed_pages = {
                page
                for page in set(old_pages) | set(new_pages)
                if old_pages.get(page) != new_pages.get(page)
            }
            status = "changed"
        reference_source = new or old
        assert reference_source is not None
        changed_sources.append(
            {
                "source_id": source_id,
                "status": status,
                "old_version": old.get("version") if old else None,
                "new_version": new.get("version") if new else None,
                "old_sha256": old.get("sha256") if old else None,
                "new_sha256": new.get("sha256") if new else None,
                "changed_pages": sorted(changed_pages),
            }
        )
        for item in wiki_references:
            if _reference_is_impacted(item["reference"], reference_source, changed_pages):
                impacted_wiki.setdefault(item["page"], set()).add(source_id)
        for case in witness_cases:
            if _reference_is_impacted(case["source"], reference_source, changed_pages):
                impacted_cases[case["id"]] = {
                    **case,
                    "changed_source_ids": sorted(
                        {*impacted_cases.get(case["id"], {}).get("changed_source_ids", []), source_id}
                    ),
                }
    return {
        "old_manifest": str(old_manifest),
        "new_manifest": str(new_manifest),
        "model_calls": 0,
        "changed_sources": changed_sources,
        "wiki_pages_for_review": [
            {"page": page, "changed_source_ids": sorted(source_ids)}
            for page, source_ids in sorted(impacted_wiki.items())
        ],
        "regression_cases_for_review": sorted(impacted_cases.values(), key=lambda item: item["id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-manifest", type=Path, required=True)
    parser.add_argument("--new-manifest", type=Path, required=True)
    parser.add_argument("--source-id", action="append", dest="source_ids")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = compare_manifests(
        args.old_manifest.resolve(),
        args.new_manifest.resolve(),
        source_ids=set(args.source_ids or []) or None,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
