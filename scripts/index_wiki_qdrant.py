from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

from dotenv import load_dotenv

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.wiki_store import WikiPage, WikiStore  # noqa: E402
from wiki_api.rag_index import (  # noqa: E402
    build_wiki_rag_manifest,
    delete_wiki_rag_orphaned_points,
    get_wiki_rag_status,
)


DEFAULT_COLLECTION = "foodex2_wiki_markdown_v1"
DEFAULT_MODEL = "voyage-context-3"
DEFAULT_DIMENSION = 1024
DEFAULT_CATEGORIES = "runtime,guidance,validation,domain_overlay,maintenance"
POINT_NAMESPACE = uuid.UUID("9a9c5167-6d68-47b4-b845-36e658e28c11")


def _ssl_context() -> ssl.SSLContext | None:
    return ssl.create_default_context(cafile=certifi.where()) if certifi else None


def _http_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with {exc.code}: {raw}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {url} connection failed: {exc}") from exc


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "section"


def _page_path(store: WikiStore, page_name: str) -> str:
    normalized = store.normalize_page_name(page_name)
    if normalized == "index.md":
        return str(store.index_path.relative_to(REPO_ROOT))
    if normalized == "log.md":
        return str(store.log_path.relative_to(REPO_ROOT))
    if normalized in store.root_docs:
        return str(store.root_docs[normalized].relative_to(REPO_ROOT))
    return str((store.guidance_dir / normalized).relative_to(REPO_ROOT))


def _split_markdown_sections(content: str) -> list[tuple[str, str]]:
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
                continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    return [
        (heading, "\n".join(lines).strip())
        for heading, lines in sections
        if "\n".join(lines).strip()
    ]


def _split_long_text(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    paragraphs = [paragraph for paragraph in text.split("\n\n") if paragraph.strip()]
    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 2
        if current and current_len + paragraph_len > max_chars:
            parts.append("\n\n".join(current).strip())
            current = []
            current_len = 0
        if paragraph_len > max_chars:
            for start in range(0, len(paragraph), max_chars):
                chunk = paragraph[start : start + max_chars].strip()
                if chunk:
                    parts.append(chunk)
            continue
        current.append(paragraph)
        current_len += paragraph_len
    if current:
        parts.append("\n\n".join(current).strip())
    return parts


def _chunk_page(
    *,
    store: WikiStore,
    page: WikiPage,
    max_chars: int,
) -> list[dict[str, Any]]:
    clean_content = store.clean_content_for_model(page)
    chunks: list[dict[str, Any]] = []
    for section_index, (heading_path, section_text) in enumerate(
        _split_markdown_sections(clean_content)
    ):
        for part_index, part_text in enumerate(_split_long_text(section_text, max_chars=max_chars)):
            chunk_text = (
                f"Page: {page.title}\n"
                f"File: {page.name}\n"
                f"Category: {store.page_category(page.name)}\n"
                f"Summary: {page.summary}\n"
                f"Section: {heading_path}\n\n"
                f"{part_text}"
            ).strip()
            chunk_id = f"{page.name}#{section_index:03d}-{part_index:02d}-{_slug(heading_path)}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "chunk_text": chunk_text,
                    "page_name": page.name,
                    "title": page.title,
                    "summary": page.summary,
                    "category": store.page_category(page.name),
                    "source_tier": page.source_tier,
                    "heading_path": heading_path,
                    "section_index": section_index,
                    "part_index": part_index,
                    "source_path": _page_path(store, page.name),
                    "sources": page.sources,
                    "related": page.related,
                    "content_sha256": hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                }
            )
    return chunks


def _selected_pages(store: WikiStore, categories: set[str]) -> list[WikiPage]:
    pages = []
    for page_name in sorted(store.allowed_page_names()):
        if page_name == "log.md":
            continue
        page = store.read_page(page_name)
        if store.page_category(page.name) in categories:
            pages.append(page)
    return pages


def _voyage_context_embed(
    *,
    documents: list[list[str]],
    input_type: str,
    model: str,
    dimension: int,
    timeout: float,
) -> list[list[list[float]]]:
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY is not set")
    response = _http_json(
        method="POST",
        url="https://api.voyageai.com/v1/contextualizedembeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        payload={
            "inputs": documents,
            "input_type": input_type,
            "model": model,
            "output_dimension": dimension,
            "output_dtype": "float",
        },
        timeout=timeout,
    )
    data = response.get("data") or response.get("results")
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected Voyage response shape: {response.keys()}")

    embedded_documents: list[list[list[float]]] = []
    for item in data:
        embeddings = item.get("embeddings") if isinstance(item, dict) else None
        if embeddings is None and isinstance(item, dict) and isinstance(item.get("data"), list):
            embeddings = [
                nested_item.get("embedding")
                for nested_item in item["data"]
                if isinstance(nested_item, dict)
            ]
        if not isinstance(embeddings, list) or not all(
            isinstance(embedding, list) for embedding in embeddings
        ):
            raise RuntimeError(f"Unexpected Voyage document result shape: {item}")
        embedded_documents.append(embeddings)
    return embedded_documents


def _create_collection(
    *,
    qdrant_url: str,
    collection: str,
    dimension: int,
    recreate: bool,
) -> None:
    if recreate:
        try:
            _http_json(method="DELETE", url=f"{qdrant_url}/collections/{collection}")
        except RuntimeError as exc:
            if "404" not in str(exc):
                raise
    _http_json(
        method="PUT",
        url=f"{qdrant_url}/collections/{collection}",
        payload={
            "vectors": {"size": dimension, "distance": "Cosine"},
            "on_disk_payload": True,
        },
    )


def _ensure_payload_indexes(*, qdrant_url: str, collection: str) -> None:
    for field_name in ["page_name", "category", "heading_path", "source_path"]:
        try:
            _http_json(
                method="PUT",
                url=f"{qdrant_url}/collections/{collection}/index",
                payload={
                    "field_name": field_name,
                    "field_schema": "keyword",
                },
            )
        except RuntimeError:
            # Existing indexes are harmless. Qdrant versions differ slightly in duplicate behavior.
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
        batch = points[start : start + batch_size]
        _http_json(
            method="PUT",
            url=f"{qdrant_url}/collections/{collection}/points?wait=true",
            payload={"points": batch},
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Qdrant collection from the curated FoodEx2 markdown wiki."
    )
    parser.add_argument("--collection", default=os.getenv("WIKI_QDRANT_COLLECTION", DEFAULT_COLLECTION))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    parser.add_argument("--model", default=os.getenv("WIKI_EMBED_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dimension", type=int, default=int(os.getenv("WIKI_EMBED_DIMENSION", DEFAULT_DIMENSION)))
    parser.add_argument("--categories", default=DEFAULT_CATEGORIES)
    parser.add_argument("--max-chars", type=int, default=2800)
    parser.add_argument("--doc-batch-size", type=int, default=4)
    parser.add_argument("--upsert-batch-size", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help=(
            "After upserting current markdown chunks, delete Qdrant chunks that are no longer "
            "present in the markdown-derived wiki index."
        ),
    )
    parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional path to write the expected markdown-derived wiki RAG manifest as JSON.",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    qdrant_url = args.qdrant_url.rstrip("/")
    store = WikiStore(REPO_ROOT)
    categories = {category.strip() for category in args.categories.split(",") if category.strip()}
    pages = _selected_pages(store, categories)
    chunks_by_page = [
        _chunk_page(store=store, page=page, max_chars=args.max_chars)
        for page in pages
    ]
    all_chunks = [chunk for chunks in chunks_by_page for chunk in chunks]
    if not all_chunks:
        raise RuntimeError("No chunks created")

    print(
        f"Indexing {len(all_chunks)} chunks from {len(pages)} pages into "
        f"{args.collection} ({args.model}, {args.dimension}d)."
    )
    _create_collection(
        qdrant_url=qdrant_url,
        collection=args.collection,
        dimension=args.dimension,
        recreate=args.recreate,
    )
    _ensure_payload_indexes(qdrant_url=qdrant_url, collection=args.collection)

    indexed_at = datetime.now(timezone.utc).isoformat()
    indexed_count = 0
    for start in range(0, len(chunks_by_page), args.doc_batch_size):
        page_batch = chunks_by_page[start : start + args.doc_batch_size]
        batch_chunks = [chunk for chunks in page_batch for chunk in chunks]
        batch_documents = [[chunk["chunk_text"] for chunk in chunks] for chunks in page_batch]
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
        print(f"Indexed {indexed_count}/{len(all_chunks)} chunks ({elapsed:.1f}s batch).")

    info = _http_json(method="GET", url=f"{qdrant_url}/collections/{args.collection}")
    result = info.get("result", {})
    print(
        json.dumps(
            {
                "collection": args.collection,
                "pages": len(pages),
                "chunks": len(all_chunks),
                "qdrant_points": result.get("points_count"),
                "model": args.model,
                "dimension": args.dimension,
            },
            indent=2,
        )
    )
    if args.delete_orphans:
        status_before_delete = get_wiki_rag_status(
            root=REPO_ROOT,
            collection=args.collection,
            qdrant_url=qdrant_url,
            embedding_model=args.model,
            embedding_dimension=args.dimension,
            categories=args.categories,
            max_chars=args.max_chars,
            timeout=args.timeout,
        )
        delete_result = delete_wiki_rag_orphaned_points(
            status=status_before_delete,
            qdrant_url=qdrant_url,
            timeout=args.timeout,
        )
        print(json.dumps({"orphan_delete": delete_result}, indent=2))
    if args.manifest_path:
        manifest_path = Path(args.manifest_path)
        if not manifest_path.is_absolute():
            manifest_path = REPO_ROOT / manifest_path
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                build_wiki_rag_manifest(
                    store=store,
                    collection=args.collection,
                    embedding_model=args.model,
                    embedding_dimension=args.dimension,
                    categories=args.categories,
                    max_chars=args.max_chars,
                ),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
