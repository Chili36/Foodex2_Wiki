"""Surface evidence-backed semantic audit findings, never infer gaps from counts."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess

from .wiki_store import WikiStore

MANIFEST_PATH = "docs/source-coverage.json"
TOPIC_CATEGORIES = {"guidance", "domain_overlay", "validation", "maintenance"}


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wiki_snapshot(store: WikiStore) -> dict[str, str]:
    return {
        p.name: fingerprint(p.content.encode("utf-8"))
        for p in store.catalog()
        if store.page_category(p.name) in TOPIC_CATEGORIES | {"runtime"}
        or p.name == "RUNTIME_RULES.md"
    }


def source_files(store: WikiStore) -> dict[str, Path]:
    return {
        p.relative_to(store.root).as_posix(): p
        for p in sorted((store.root / "foodex2_docs").rglob("*"))
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(store.root).parts)
    }


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_audit(data: object) -> dict:
    if not isinstance(data, dict) or data.get("version") != 2:
        raise ValueError("expected a version 2 semantic audit")
    for key in ("scope", "limitations", "reviewed_by", "report"):
        if not _text(data.get(key)):
            raise ValueError(f"{key} is required")
    try:
        if date.fromisoformat(data.get("reviewed_at", "")) > date.today():
            raise ValueError("future date")
    except (TypeError, ValueError) as exc:
        raise ValueError("reviewed_at must be a non-future ISO date") from exc
    for key in ("source_snapshot", "wiki_snapshot"):
        values = data.get(key)
        if (
            not isinstance(values, dict)
            or not values
            or not all(
                _text(k)
                and isinstance(v, str)
                and len(v) == 64
                and all(c in "0123456789abcdef" for c in v)
                for k, v in values.items()
            )
        ):
            raise ValueError(f"{key} requires paths and SHA-256 fingerprints")
    roles = data.get("source_roles", {})
    if not isinstance(roles, dict) or not all(
        _text(k) and _text(v) for k, v in roles.items()
    ):
        raise ValueError("source_roles must map source paths to role descriptions")
    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings must be an array")
    seen = set()
    for item in findings:
        if not isinstance(item, dict):
            raise ValueError("each finding must be an object")
        for key in (
            "id",
            "source",
            "locator",
            "source_excerpt",
            "observation",
            "action",
            "title",
        ):
            if not _text(item.get(key)):
                raise ValueError(f"finding requires {key}")
        if item["id"] in seen:
            raise ValueError(f"duplicate finding id: {item['id']}")
        seen.add(item["id"])
        if item.get("status") not in ("open", "resolved"):
            raise ValueError(f"{item['id']}: invalid status")
        if item["source"] not in data["source_snapshot"]:
            raise ValueError(f"{item['id']}: source is not fingerprinted")
        targets = item.get("wiki_pages")
        if (
            not isinstance(targets, list)
            or not targets
            or not all(
                isinstance(p, str) and p in data["wiki_snapshot"] for p in targets
            )
        ):
            raise ValueError(
                f"{item['id']}: wiki_pages must identify inspected topic pages"
            )
        if item["status"] == "resolved" and not _text(item.get("resolution")):
            raise ValueError(
                f"{item['id']}: resolved finding requires a resolution note"
            )
    return data


def audit_source_coverage(store: WikiStore) -> dict:
    """Read a semantic audit and check its freshness. Does not perform semantic analysis."""
    sources = source_files(store)
    snapshot = wiki_snapshot(store)
    report = {
        "source_count": len(sources),
        "topic_page_count": sum(
            store.page_category(name) in TOPIC_CATEGORIES for name in snapshot
        ),
        "topic_word_count": sum(
            len(store.read_page(name).body.split())
            for name in snapshot
            if store.page_category(name) in TOPIC_CATEGORIES
        ),
        "audit_status": "not_run",
        "open_finding_count": 0,
        "information": "Source coverage has not been semantically audited. Missing review records are not content gaps.",
        "sources": [{"source": name, "role": "not classified"} for name in sources],
        "recorded_findings": [],
        "findings": [],
    }
    path = store.root / MANIFEST_PATH
    if not path.exists():
        return report
    try:
        data = _validate_audit(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        report["audit_status"] = "invalid"
        report["information"] = (
            "The saved audit could not be validated; no content-gap claims were emitted."
        )
        report["findings"].append(
            {
                "severity": "warning",
                "check": "source_coverage_audit",
                "location": MANIFEST_PATH,
                "message": f"Invalid saved audit: {exc}",
            }
        )
        return report

    changed_sources = [
        name
        for name, digest in data["source_snapshot"].items()
        if name not in sources or fingerprint(sources[name].read_bytes()) != digest
    ]
    changed_pages = sorted(
        name
        for name in set(snapshot) | set(data["wiki_snapshot"])
        if snapshot.get(name) != data["wiki_snapshot"].get(name)
    )
    stale = bool(changed_sources or changed_pages)
    report.update(
        {
            "audit_status": "stale" if stale else "current",
            "scope": data["scope"],
            "limitations": data["limitations"],
            "report": data["report"],
            "reviewed_at": data["reviewed_at"],
            "information": f"Semantic audit ({data['reviewed_at']}): {data['scope']} {data['limitations']}",
            "sources": [
                {
                    "source": name,
                    "role": data.get("source_roles", {}).get(name, "not classified"),
                }
                for name in sources
            ],
            "recorded_findings": data["findings"],
            "changed_sources": changed_sources,
            "changed_pages": changed_pages,
            "open_finding_count": sum(f["status"] == "open" for f in data["findings"]),
        }
    )
    if stale:
        details = [*changed_sources, *changed_pages]
        report["findings"].append(
            {
                "severity": "warning",
                "check": "source_coverage_audit",
                "location": MANIFEST_PATH,
                "message": "Saved semantic audit is stale; recheck its findings before treating them as current gaps. "
                "Changed/added/removed: " + ", ".join(details) + ".",
            }
        )
    else:
        for finding in data["findings"]:
            if finding["status"] != "open":
                continue
            page_name = finding["wiki_pages"][0]
            page_path = store.root_docs.get(page_name, store.guidance_dir / page_name)
            report["findings"].append(
                {
                    "severity": "warning",
                    "check": "source_coverage",
                    "location": page_path.relative_to(store.root).as_posix(),
                    "message": f"{finding['id']} — {finding['title']}. {finding['observation']} "
                    f"Source: {Path(finding['source']).name}, {finding['locator']}. "
                    f"Action: {finding['action']}",
                }
            )
    return report


def prepare_review(root: Path, output: Path) -> None:
    """Explicit, read-only-to-corpus preparation for a human/agent semantic review."""
    store = WikiStore(root)
    for protected in (root / "foodex2_docs", root / "raw" / "efsa-guidance"):
        if output.resolve().is_relative_to(protected.resolve()):
            raise ValueError(
                "Review output must be outside the source and wiki directories."
            )
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    output.mkdir(parents=True)
    pages_dir = output / "wiki"
    pages_dir.mkdir()
    for name in wiki_snapshot(store):
        (pages_dir / name).write_text(store.read_page(name).content, encoding="utf-8")
    inventory = []
    for number, (name, path) in enumerate(source_files(store).items(), 1):
        entry = {"source": name, "sha256": fingerprint(path.read_bytes())}
        if path.suffix.lower() == ".pdf":
            try:
                result = subprocess.run(
                    ["pdftotext", "-layout", str(path), "-"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60,
                )
                pages = result.stdout.split("\f")
                if pages and not pages[-1].strip():
                    pages.pop()
                entry.update(
                    {
                        "pdf_pages": len(pages),
                        "extracted_words": len(result.stdout.split()),
                        "visual_review_required": True,
                    }
                )
                text_path = f"source-{number:02}.txt"
                (output / text_path).write_text(
                    "\n".join(
                        f"=== PDF PAGE {n} ===\n{text}"
                        for n, text in enumerate(pages, 1)
                    ),
                    encoding="utf-8",
                )
                entry["extracted_text"] = text_path
                if not pages or len(result.stdout.split()) / len(pages) < 80:
                    entry["extraction_note"] = (
                        "Sparse text: inspect rendered pages or OCR; do not infer omissions from this extraction."
                    )
            except (OSError, subprocess.SubprocessError) as exc:
                entry["extraction_note"] = (
                    f"Extraction failed; visual review/OCR required: {exc}"
                )
        else:
            entry["extraction_note"] = (
                "Inspect the original source with a suitable Markdown/CSV/spreadsheet reader."
            )
        inventory.append(entry)
    (output / "inventory.json").write_text(
        json.dumps(
            {
                "sources": inventory,
                "wiki_snapshot": wiki_snapshot(store),
                "instruction": "This is review input, not a coverage result. Compare source sections with ALL wiki pages. "
                "Record only evidence-backed, in-scope omissions; consider source age and authority. "
                "Do not promote training examples or old catalogue codes into current rules. "
                "Document inspected page ranges, exclusions, and extraction limitations.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare source and wiki evidence for an explicit semantic coverage audit."
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--prepare-review",
        type=Path,
        required=True,
        metavar="NEW_DIRECTORY",
        help="Extract local PDF text and snapshot wiki pages; a human/agent must interpret them.",
    )
    args = parser.parse_args(argv)
    prepare_review(args.root, args.prepare_review)
    print(
        f"Prepared review inputs in {args.prepare_review}. No semantic verdict has been generated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
