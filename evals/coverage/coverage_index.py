"""Build a no-LLM map from source regions to existing witness tests.

Only explicit page references receive section-level credit. A broad source citation is
reported, but it does not make every page in that source look covered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).parent / "sources" / "manifest.yaml"
PAGE_RE = re.compile(r"\b(?:p(?:p|ages?)?\.?)[ ]*(\d+)(?:[ ]*[-–—][ ]*(\d+))?", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_local_path(source: dict[str, Any]) -> Path:
    value = source.get("path")
    if not value:
        raise FileNotFoundError(
            f"{source.get('id', 'source')} is URL-only; materialize it locally and add path "
            "before chunking (the wiki is never used as a fallback)"
        )
    path = Path(str(value))
    return path if path.is_absolute() else REPO_ROOT / path


def load_manifest(path: Path, *, verify_hashes: bool = True) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{path} must contain a non-empty sources list")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("every source manifest entry must be an object")
        source_id = str(source.get("id") or "").strip()
        if not source_id or source_id in seen:
            raise ValueError(f"invalid or duplicate source id: {source_id!r}")
        seen.add(source_id)
        if not source.get("path") and not source.get("url"):
            raise ValueError(f"{source_id} needs path or url")
        if source.get("path"):
            local_path = source_local_path(source)
            if not local_path.is_file():
                raise FileNotFoundError(
                    f"authoritative source is missing: {local_path}; wiki content is not a fallback"
                )
            if verify_hashes:
                actual = sha256_file(local_path)
                expected = str(source.get("sha256") or "")
                if actual != expected:
                    raise ValueError(
                        f"sha256 mismatch for {source_id}: expected {expected}, got {actual}"
                    )
    return sources


def pdf_pages(path: Path) -> list[tuple[int, str]]:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("pdftotext is required to inspect PDF source sections") from exc
    return [
        (number, text.strip())
        for number, text in enumerate(result.stdout.split("\f"), start=1)
        if text.strip()
    ]


def source_sections(source: dict[str, Any]) -> list[dict[str, Any]]:
    path = source_local_path(source)
    if path.suffix.lower() == ".pdf":
        sections = []
        for page, text in pdf_pages(path):
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            sections.append(
                {
                    "chunk_id": f"{source['id']}:p{page:04d}",
                    "page_start": page,
                    "page_end": page,
                    "content_sha256": content_hash,
                }
            )
        return sections
    text = path.read_text(encoding="utf-8")
    sections = []
    for index, block in enumerate(re.split(r"(?m)(?=^#{1,6} )", text), start=1):
        block = block.strip()
        if not block:
            continue
        heading = block.splitlines()[0].lstrip("# ").strip() or f"section-{index}"
        content_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
        sections.append(
            {
                "chunk_id": f"{source['id']}:s{index:04d}",
                "section": heading,
                "content_sha256": content_hash,
            }
        )
    return sections


def iter_cases(root: Path) -> Iterable[dict[str, Any]]:
    for path in sorted((root / "evals").rglob("*.json")):
        if Path(__file__).parent in path.parents or "reports" in path.parts:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cases = payload.get("cases") if isinstance(payload, dict) else None
        if not isinstance(cases, list):
            continue
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict) or not isinstance(case.get("source"), str):
                continue
            yield {
                "id": str(case.get("id") or f"{path.stem}:{index}"),
                "source": case["source"],
                "file": str(path.relative_to(root)),
            }


def source_aliases(source: dict[str, Any]) -> list[str]:
    values = [source["id"], source.get("title", ""), Path(str(source.get("path", ""))).name]
    values.extend(source.get("aliases") or [])
    return sorted({str(value).casefold() for value in values if str(value).strip()}, key=len, reverse=True)


def citation_pages(citation: str, source: dict[str, Any]) -> set[int] | None:
    folded = citation.casefold()
    positions = [folded.find(alias) for alias in source_aliases(source) if alias in folded]
    if not positions:
        return None
    start = min(positions)
    segment_end = citation.find(";", start)
    segment = citation[start : segment_end if segment_end >= 0 else len(citation)]
    pages: set[int] = set()
    for match in PAGE_RE.finditer(segment):
        first = int(match.group(1))
        last = int(match.group(2) or first)
        pages.update(range(min(first, last), max(first, last) + 1))
    return pages


def build_index(manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    sources = load_manifest(manifest_path)
    cases = list(iter_cases(REPO_ROOT))
    source_reports: list[dict[str, Any]] = []
    unmatched = {case["id"]: case for case in cases}
    for source in sources:
        sections = source_sections(source)
        matching_cases: list[dict[str, Any]] = []
        targeted_pages: dict[int, list[str]] = {}
        broad_cases: list[str] = []
        for case in cases:
            pages = citation_pages(case["source"], source)
            if pages is None:
                continue
            unmatched.pop(case["id"], None)
            matching_cases.append(case)
            if not pages:
                broad_cases.append(case["id"])
            for page in pages:
                targeted_pages.setdefault(page, []).append(case["id"])
        covered = []
        uncovered = []
        for section in sections:
            page = section.get("page_start")
            test_ids = sorted(set(targeted_pages.get(page, []))) if isinstance(page, int) else []
            item = {**section, "test_ids": test_ids}
            (covered if test_ids else uncovered).append(item)
        total = len(sections)
        source_reports.append(
            {
                "source_id": source["id"],
                "title": source.get("title"),
                "version": source.get("version"),
                "section_count": total,
                "covered_section_count": len(covered),
                "coverage_percent": round(100 * len(covered) / total, 2) if total else 0.0,
                "matching_tests": matching_cases,
                "broad_source_citations_not_credited": sorted(broad_cases),
                "covered_sections": covered,
                "uncovered_sections": uncovered,
            }
        )
    total_sections = sum(item["section_count"] for item in source_reports)
    covered_sections = sum(item["covered_section_count"] for item in source_reports)
    return {
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "model_calls": 0,
        "test_case_count_with_source": len(cases),
        "source_count": len(sources),
        "section_count": total_sections,
        "covered_section_count": covered_sections,
        "coverage_percent": round(100 * covered_sections / total_sections, 2) if total_sections else 0.0,
        "sources": source_reports,
        "unmatched_test_sources": sorted(unmatched.values(), key=lambda item: item["id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    report = build_index(args.manifest.resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=None if args.compact else 2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
