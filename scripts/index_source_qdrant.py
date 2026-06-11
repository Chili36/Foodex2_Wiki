from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.index_wiki_qdrant import (  # noqa: E402
    DEFAULT_DIMENSION,
    DEFAULT_MODEL,
    _create_collection,
    _http_json,
    _split_long_text,
    _voyage_context_embed,
)


DEFAULT_COLLECTION = "foodex2_source_docs_v1"
POINT_NAMESPACE = uuid.UUID("f25f9a85-2d6e-4fcb-9c3d-6ea2b65d68cc")
SUPPORTED_SUFFIXES = {".pdf", ".md", ".csv", ".xlsx"}


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part)[:90] or "source"


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _pdf_text_layer_pages(path: Path) -> list[tuple[int, str]]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    pages = []
    for index, page_text in enumerate(result.stdout.split("\f"), start=1):
        cleaned = _clean_text(page_text)
        if cleaned:
            pages.append((index, cleaned))
    return pages


def _page_number_from_image(path: Path) -> int:
    match = re.search(r"-(\d+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def _ocr_image(image_path: Path) -> tuple[int, str]:
    result = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", "eng"],
        check=True,
        capture_output=True,
        text=True,
    )
    return _page_number_from_image(image_path), _clean_text(result.stdout)


def _ocr_pdf_pages(path: Path) -> list[tuple[int, str]]:
    with tempfile.TemporaryDirectory(prefix="foodex2-source-ocr-") as temp_dir:
        prefix = Path(temp_dir) / "page"
        subprocess.run(
            ["pdftoppm", "-r", "200", "-png", str(path), str(prefix)],
            check=True,
            capture_output=True,
            text=True,
        )
        image_paths = sorted(Path(temp_dir).glob("page-*.png"), key=_page_number_from_image)
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(image_paths)))) as executor:
            pages = list(executor.map(_ocr_image, image_paths))
    return [(page_number, text) for page_number, text in pages if text]


def _should_ocr_pdf(pages: list[tuple[int, str]]) -> bool:
    if len(pages) < 20:
        return False
    total_chars = sum(len(text) for _, text in pages)
    average_chars = total_chars / len(pages)
    sparse_pages = sum(1 for _, text in pages if len(text) < 250)
    return average_chars < 700 and sparse_pages / len(pages) > 0.25


def _pdf_pages(path: Path) -> list[tuple[int, str]]:
    pages = _pdf_text_layer_pages(path)
    if (
        pages
        and _should_ocr_pdf(pages)
        and shutil.which("pdftoppm")
        and shutil.which("tesseract")
    ):
        try:
            ocr_pages = _ocr_pdf_pages(path)
        except (OSError, subprocess.CalledProcessError):
            return pages
        if sum(len(text) for _, text in ocr_pages) > sum(len(text) for _, text in pages) * 1.5:
            return ocr_pages
    return pages


def _markdown_sections(path: Path) -> list[tuple[str, str]]:
    content = path.read_text(encoding="utf-8")
    sections: list[tuple[str, list[str]]] = []
    current_heading = "overview"
    current_lines: list[str] = []
    heading_stack: list[tuple[int, str]] = []
    for line in content.splitlines():
        if line.startswith("#"):
            stripped = line.lstrip("#")
            level = len(line) - len(stripped)
            if 1 <= level <= 6 and stripped.startswith(" "):
                if current_lines:
                    sections.append((current_heading, current_lines))
                    current_lines = []
                title = stripped.strip()
                heading_stack = [(lvl, text) for lvl, text in heading_stack if lvl < level]
                heading_stack.append((level, title))
                current_heading = " > ".join(text for _, text in heading_stack)
        current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))
    return [
        (heading, "\n".join(lines).strip())
        for heading, lines in sections
        if "\n".join(lines).strip()
    ]


def _csv_chunks(path: Path, *, rows_per_chunk: int) -> list[tuple[str, str]]:
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        for row in reader:
            rows.append({field: row.get(field, "") for field in fieldnames})
    chunks = []
    for start in range(0, len(rows), rows_per_chunk):
        batch = rows[start : start + rows_per_chunk]
        label = f"rows {start + 1}-{start + len(batch)}"
        text = "\n".join(json.dumps(row, ensure_ascii=False) for row in batch)
        chunks.append((label, text))
    return chunks


def _xlsx_text(path: Path) -> str:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("main:si", ns):
                parts = [node.text or "" for node in item.findall(".//main:t", ns)]
                shared_strings.append("".join(parts))

        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
            if "Id" in rel.attrib and "Target" in rel.attrib
        }
        sections: list[str] = []
        for sheet in workbook.findall(".//main:sheet", ns):
            sheet_name = sheet.attrib.get("name", "sheet")
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_targets.get(rel_id or "")
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/")
            if sheet_path not in archive.namelist():
                sheet_path = "xl/worksheets/" + Path(target).name
            if sheet_path not in archive.namelist():
                continue
            sheet_root = ElementTree.fromstring(archive.read(sheet_path))
            rows: list[str] = [f"Sheet: {sheet_name}"]
            for row in sheet_root.findall(".//main:row", ns):
                values = []
                for cell in row.findall("main:c", ns):
                    raw_value = cell.findtext("main:v", default="", namespaces=ns)
                    if cell.attrib.get("t") == "s" and raw_value.isdigit():
                        index = int(raw_value)
                        value = shared_strings[index] if index < len(shared_strings) else raw_value
                    else:
                        value = raw_value
                    if value:
                        values.append(value)
                if values:
                    rows.append(" | ".join(values))
            if len(rows) > 1:
                sections.append("\n".join(rows))
    return "\n\n".join(sections)


def _source_files(source_dir: Path) -> list[Path]:
    source_dir = source_dir.resolve()
    return [
        path
        for path in sorted(source_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]


def _chunks_for_file(path: Path, *, max_chars: int, rows_per_chunk: int) -> list[dict[str, Any]]:
    relative_path = str(path.relative_to(REPO_ROOT))
    suffix = path.suffix.lower()
    base_payload = {
        "source_file": path.name,
        "source_path": relative_path,
        "source_suffix": suffix.lstrip("."),
    }
    chunks: list[dict[str, Any]] = []

    if suffix == ".pdf":
        for page_number, page_text in _pdf_pages(path):
            for part_index, part_text in enumerate(_split_long_text(page_text, max_chars=max_chars)):
                location = f"page {page_number}"
                chunk_text = (
                    f"Source file: {path.name}\n"
                    f"Source path: {relative_path}\n"
                    f"Format: PDF\n"
                    f"Location: {location}\n\n"
                    f"{part_text}"
                ).strip()
                chunks.append(
                    {
                        **base_payload,
                        "location": location,
                        "page_number": page_number,
                        "part_index": part_index,
                        "chunk_text": chunk_text,
                    }
                )
    elif suffix == ".md":
        for section_index, (heading, section_text) in enumerate(_markdown_sections(path)):
            for part_index, part_text in enumerate(_split_long_text(section_text, max_chars=max_chars)):
                chunk_text = (
                    f"Source file: {path.name}\n"
                    f"Source path: {relative_path}\n"
                    f"Format: Markdown\n"
                    f"Location: {heading}\n\n"
                    f"{part_text}"
                ).strip()
                chunks.append(
                    {
                        **base_payload,
                        "location": heading,
                        "section_index": section_index,
                        "part_index": part_index,
                        "chunk_text": chunk_text,
                    }
                )
    elif suffix == ".csv":
        for section_index, (label, text) in enumerate(_csv_chunks(path, rows_per_chunk=rows_per_chunk)):
            for part_index, part_text in enumerate(_split_long_text(text, max_chars=max_chars)):
                chunk_text = (
                    f"Source file: {path.name}\n"
                    f"Source path: {relative_path}\n"
                    f"Format: CSV\n"
                    f"Location: {label}\n\n"
                    f"{part_text}"
                ).strip()
                chunks.append(
                    {
                        **base_payload,
                        "location": label,
                        "section_index": section_index,
                        "part_index": part_index,
                        "chunk_text": chunk_text,
                    }
                )
    elif suffix == ".xlsx":
        text = _xlsx_text(path)
        for part_index, part_text in enumerate(_split_long_text(text, max_chars=max_chars)):
            chunk_text = (
                f"Source file: {path.name}\n"
                f"Source path: {relative_path}\n"
                f"Format: XLSX\n"
                f"Location: workbook text\n\n"
                f"{part_text}"
            ).strip()
            chunks.append(
                {
                    **base_payload,
                    "location": "workbook text",
                    "part_index": part_index,
                    "chunk_text": chunk_text,
                }
            )

    for index, chunk in enumerate(chunks):
        chunk_id = (
            f"{relative_path}#{index:04d}-"
            f"{_slug(str(chunk.get('location', 'source')))}-"
            f"{chunk.get('part_index', 0):02d}"
        )
        chunk["chunk_id"] = chunk_id
        chunk["content_sha256"] = hashlib.sha256(chunk["chunk_text"].encode("utf-8")).hexdigest()
    return chunks


def _ensure_payload_indexes(*, qdrant_url: str, collection: str) -> None:
    for field_name in ["source_file", "source_path", "source_suffix", "location"]:
        try:
            _http_json(
                method="PUT",
                url=f"{qdrant_url}/collections/{collection}/index",
                payload={"field_name": field_name, "field_schema": "keyword"},
            )
        except RuntimeError:
            pass


def _upsert_points(
    *,
    qdrant_url: str,
    collection: str,
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
    indexed_at: str,
    model: str,
    dimension: int,
    batch_size: int,
) -> None:
    points = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        point_id = str(uuid.uuid5(POINT_NAMESPACE, chunk["chunk_id"]))
        payload = {
            **chunk,
            "content": chunk["chunk_text"],
            "embedding_provider": "voyage",
            "embedding_model": model,
            "embedding_dimension": dimension,
            "indexed_at": indexed_at,
        }
        payload.pop("chunk_text", None)
        points.append({"id": point_id, "vector": vector, "payload": payload})

    for start in range(0, len(points), batch_size):
        _http_json(
            method="PUT",
            url=f"{qdrant_url}/collections/{collection}/points?wait=true",
            payload={"points": points[start : start + batch_size]},
        )


def _embedding_documents(
    chunks_by_file: list[list[dict[str, Any]]],
    *,
    max_document_chars: int,
) -> list[list[dict[str, Any]]]:
    documents: list[list[dict[str, Any]]] = []
    for file_chunks in chunks_by_file:
        current: list[dict[str, Any]] = []
        current_chars = 0
        for chunk in file_chunks:
            chunk_chars = len(chunk["chunk_text"])
            if current and current_chars + chunk_chars > max_document_chars:
                documents.append(current)
                current = []
                current_chars = 0
            current.append(chunk)
            current_chars += chunk_chars
        if current:
            documents.append(current)
    return documents


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Qdrant collection from immutable FoodEx2 source documents."
    )
    parser.add_argument("--collection", default=os.getenv("SOURCE_QDRANT_COLLECTION", DEFAULT_COLLECTION))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    parser.add_argument("--source-dir", type=Path, default=REPO_ROOT / "foodex2_docs")
    parser.add_argument("--model", default=os.getenv("SOURCE_EMBED_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dimension", type=int, default=int(os.getenv("SOURCE_EMBED_DIMENSION", DEFAULT_DIMENSION)))
    parser.add_argument("--max-chars", type=int, default=3200)
    parser.add_argument(
        "--max-document-chars",
        type=int,
        default=50000,
        help=(
            "Maximum total characters per contextualized embedding document. "
            "Large PDFs are windowed so they fit Voyage's context limit."
        ),
    )
    parser.add_argument("--rows-per-chunk", type=int, default=40)
    parser.add_argument("--doc-batch-size", type=int, default=2)
    parser.add_argument("--upsert-batch-size", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    qdrant_url = args.qdrant_url.rstrip("/")
    source_files = _source_files(args.source_dir)
    chunks_by_file = [
        _chunks_for_file(path, max_chars=args.max_chars, rows_per_chunk=args.rows_per_chunk)
        for path in source_files
    ]
    all_chunks = [chunk for chunks in chunks_by_file for chunk in chunks]
    if not all_chunks:
        raise RuntimeError(f"No source chunks created from {args.source_dir}")

    print(
        f"Indexing {len(all_chunks)} chunks from {len(source_files)} source files into "
        f"{args.collection} ({args.model}, {args.dimension}d).",
        flush=True,
    )
    _create_collection(
        qdrant_url=qdrant_url,
        collection=args.collection,
        dimension=args.dimension,
        recreate=args.recreate,
    )
    _ensure_payload_indexes(qdrant_url=qdrant_url, collection=args.collection)

    indexed_at = datetime.now(timezone.utc).isoformat()
    embedding_documents = _embedding_documents(
        chunks_by_file,
        max_document_chars=args.max_document_chars,
    )
    indexed_count = 0
    for start in range(0, len(embedding_documents), args.doc_batch_size):
        document_batch = embedding_documents[start : start + args.doc_batch_size]
        batch_chunks = [chunk for chunks in document_batch for chunk in chunks]
        batch_documents = [[chunk["chunk_text"] for chunk in chunks] for chunks in document_batch]
        if not batch_documents:
            continue
        started = time.perf_counter()
        embedded_docs = _voyage_context_embed(
            documents=batch_documents,
            input_type="document",
            model=args.model,
            dimension=args.dimension,
            timeout=args.timeout,
        )
        batch_vectors = [vector for vectors in embedded_docs for vector in vectors]
        if len(batch_vectors) != len(batch_chunks):
            raise RuntimeError(
                f"Voyage returned {len(batch_vectors)} vectors for {len(batch_chunks)} chunks"
            )
        _upsert_points(
            qdrant_url=qdrant_url,
            collection=args.collection,
            chunks=batch_chunks,
            vectors=batch_vectors,
            indexed_at=indexed_at,
            model=args.model,
            dimension=args.dimension,
            batch_size=args.upsert_batch_size,
        )
        indexed_count += len(batch_chunks)
        elapsed = time.perf_counter() - started
        print(f"Indexed {indexed_count}/{len(all_chunks)} chunks ({elapsed:.1f}s batch).", flush=True)

    info = _http_json(method="GET", url=f"{qdrant_url}/collections/{args.collection}")
    result = info.get("result", {})
    print(
        json.dumps(
            {
                "collection": args.collection,
                "source_files": len(source_files),
                "chunks": len(all_chunks),
                "qdrant_points": result.get("points_count"),
                "model": args.model,
                "dimension": args.dimension,
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
