from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import uuid
from typing import Any

from .qdrant_ask import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_WIKI_COLLECTION,
    QdrantAskError,
    _http_json,
)
from .wiki_store import WikiPage, WikiStore


DEFAULT_WIKI_CATEGORIES = "runtime,guidance,validation,domain_overlay,maintenance"
DEFAULT_WIKI_CHUNK_MAX_CHARS = 2800
POINT_NAMESPACE = uuid.UUID("9a9c5167-6d68-47b4-b845-36e658e28c11")
STATUS_PAYLOAD_FIELDS = [
    "chunk_id",
    "page_name",
    "content_sha256",
    "source_path",
    "embedding_provider",
    "embedding_model",
    "embedding_dimension",
    "indexed_at",
]


@dataclass(frozen=True)
class WikiRagChunkSet:
    pages: list[WikiPage]
    chunks: list[dict[str, Any]]
    categories: set[str]
    max_chars: int


def point_id_for_chunk_id(chunk_id: str) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, chunk_id))


def parse_categories(raw_categories: str | list[str] | set[str]) -> set[str]:
    if isinstance(raw_categories, str):
        return {category.strip() for category in raw_categories.split(",") if category.strip()}
    return {str(category).strip() for category in raw_categories if str(category).strip()}


def build_wiki_rag_chunks(
    *,
    store: WikiStore,
    categories: str | list[str] | set[str] = DEFAULT_WIKI_CATEGORIES,
    max_chars: int = DEFAULT_WIKI_CHUNK_MAX_CHARS,
) -> WikiRagChunkSet:
    selected_categories = parse_categories(categories)
    pages = _selected_pages(store, selected_categories)
    chunks_by_page = [
        _chunk_page(store=store, page=page, max_chars=max_chars)
        for page in pages
    ]
    return WikiRagChunkSet(
        pages=pages,
        chunks=[chunk for chunks in chunks_by_page for chunk in chunks],
        categories=selected_categories,
        max_chars=max_chars,
    )


def build_wiki_rag_manifest(
    *,
    store: WikiStore,
    collection: str = DEFAULT_WIKI_COLLECTION,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    categories: str | list[str] | set[str] = DEFAULT_WIKI_CATEGORIES,
    max_chars: int = DEFAULT_WIKI_CHUNK_MAX_CHARS,
) -> dict[str, Any]:
    chunk_set = build_wiki_rag_chunks(store=store, categories=categories, max_chars=max_chars)
    chunks_by_page: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunk_set.chunks:
        chunks_by_page.setdefault(chunk["page_name"], []).append(chunk)

    pages = []
    for page in chunk_set.pages:
        page_chunks = chunks_by_page.get(page.name, [])
        page_hash_input = "\n".join(chunk["content_sha256"] for chunk in page_chunks)
        pages.append(
            {
                "page_name": page.name,
                "title": page.title,
                "category": page_chunks[0]["category"]
                if page_chunks and page_chunks[0].get("category")
                else store.page_category(page.name),
                "source_path": _page_path(store, page.name),
                "chunk_count": len(page_chunks),
                "content_hash": hashlib.sha256(page_hash_input.encode("utf-8")).hexdigest(),
                "chunk_hashes": [chunk["content_sha256"] for chunk in page_chunks],
                "chunk_ids": [chunk["chunk_id"] for chunk in page_chunks],
            }
        )

    return {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collection": collection,
        "embedding_provider": "voyage",
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dimension,
        "chunking": {
            "strategy": "markdown-heading-sections-with-paragraph-splitting",
            "max_chars": max_chars,
            "categories": sorted(chunk_set.categories),
        },
        "page_count": len(pages),
        "chunk_count": len(chunk_set.chunks),
        "pages": pages,
    }


def get_wiki_rag_status(
    *,
    root: Path | str,
    collection: str | None = None,
    qdrant_url: str | None = None,
    embedding_model: str | None = None,
    embedding_dimension: int | None = None,
    categories: str | list[str] | set[str] = DEFAULT_WIKI_CATEGORIES,
    max_chars: int = DEFAULT_WIKI_CHUNK_MAX_CHARS,
    timeout: float = 30.0,
) -> dict[str, Any]:
    store = WikiStore(root)
    effective_collection = collection or os.getenv("WIKI_QDRANT_COLLECTION", DEFAULT_WIKI_COLLECTION)
    effective_qdrant_url = (qdrant_url or os.getenv("QDRANT_URL", "http://127.0.0.1:6333")).rstrip("/")
    effective_model = embedding_model or os.getenv("WIKI_EMBED_MODEL", DEFAULT_EMBEDDING_MODEL)
    effective_dimension = embedding_dimension or int(
        os.getenv("WIKI_EMBED_DIMENSION", str(DEFAULT_EMBEDDING_DIMENSION))
    )
    chunk_set = build_wiki_rag_chunks(store=store, categories=categories, max_chars=max_chars)
    expected_by_chunk_id = {chunk["chunk_id"]: chunk for chunk in chunk_set.chunks}
    expected_pages = {page.name for page in chunk_set.pages}

    base_status: dict[str, Any] = {
        "ok": False,
        "collection": effective_collection,
        "qdrant_url": effective_qdrant_url,
        "embedding_provider": "voyage",
        "embedding_model": effective_model,
        "embedding_dimension": effective_dimension,
        "chunking": {
            "max_chars": max_chars,
            "categories": sorted(chunk_set.categories),
        },
        "expected": {
            "page_count": len(expected_pages),
            "chunk_count": len(expected_by_chunk_id),
            "pages": sorted(expected_pages),
        },
        "indexed": {
            "collection_exists": False,
            "points_count": None,
            "chunk_count": 0,
            "page_count": 0,
            "pages": [],
            "payloadless_points": 0,
            "duplicate_chunk_ids": [],
        },
        "drift": {
            "missing_pages": [],
            "stale_pages": [],
            "orphaned_pages": [],
            "missing_chunk_ids": [],
            "stale_chunk_ids": [],
            "orphaned_chunk_ids": [],
            "embedding_model_mismatch_chunk_ids": [],
            "embedding_dimension_mismatch_chunk_ids": [],
        },
        "errors": [],
    }

    try:
        collection_info = _get_collection_info(
            qdrant_url=effective_qdrant_url,
            collection=effective_collection,
            timeout=timeout,
        )
        indexed_points = _scroll_collection_points(
            qdrant_url=effective_qdrant_url,
            collection=effective_collection,
            timeout=timeout,
        )
    except QdrantAskError as exc:
        base_status["errors"].append(str(exc))
        return base_status

    indexed_by_chunk_id: dict[str, dict[str, Any]] = {}
    duplicate_chunk_ids: list[str] = []
    payloadless_points = 0
    for point in indexed_points:
        payload = point.get("payload")
        if not isinstance(payload, dict):
            payloadless_points += 1
            continue
        chunk_id = payload.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id:
            payloadless_points += 1
            continue
        if chunk_id in indexed_by_chunk_id:
            duplicate_chunk_ids.append(chunk_id)
            continue
        indexed_by_chunk_id[chunk_id] = {
            "id": point.get("id"),
            "payload": payload,
        }

    indexed_pages = {
        payload["payload"].get("page_name")
        for payload in indexed_by_chunk_id.values()
        if isinstance(payload["payload"].get("page_name"), str)
    }
    missing_chunk_ids = sorted(set(expected_by_chunk_id) - set(indexed_by_chunk_id))
    orphaned_chunk_ids = sorted(set(indexed_by_chunk_id) - set(expected_by_chunk_id))
    stale_chunk_ids: list[str] = []
    model_mismatch_chunk_ids: list[str] = []
    dimension_mismatch_chunk_ids: list[str] = []

    for chunk_id in sorted(set(expected_by_chunk_id) & set(indexed_by_chunk_id)):
        expected = expected_by_chunk_id[chunk_id]
        payload = indexed_by_chunk_id[chunk_id]["payload"]
        if payload.get("content_sha256") != expected["content_sha256"]:
            stale_chunk_ids.append(chunk_id)
        if payload.get("embedding_model") != effective_model:
            model_mismatch_chunk_ids.append(chunk_id)
        if payload.get("embedding_dimension") != effective_dimension:
            dimension_mismatch_chunk_ids.append(chunk_id)

    stale_source_chunk_ids = set(
        missing_chunk_ids
        + stale_chunk_ids
        + model_mismatch_chunk_ids
        + dimension_mismatch_chunk_ids
    )
    stale_pages = sorted(
        {
            expected_by_chunk_id[chunk_id]["page_name"]
            for chunk_id in stale_source_chunk_ids
            if chunk_id in expected_by_chunk_id
        }
    )

    base_status["indexed"] = {
        "collection_exists": True,
        "points_count": _points_count(collection_info),
        "chunk_count": len(indexed_by_chunk_id),
        "page_count": len(indexed_pages),
        "pages": sorted(indexed_pages),
        "payloadless_points": payloadless_points,
        "duplicate_chunk_ids": sorted(set(duplicate_chunk_ids)),
    }
    base_status["drift"] = {
        "missing_pages": sorted(expected_pages - indexed_pages),
        "stale_pages": stale_pages,
        "orphaned_pages": sorted(indexed_pages - expected_pages),
        "missing_chunk_ids": missing_chunk_ids,
        "stale_chunk_ids": stale_chunk_ids,
        "orphaned_chunk_ids": orphaned_chunk_ids,
        "embedding_model_mismatch_chunk_ids": model_mismatch_chunk_ids,
        "embedding_dimension_mismatch_chunk_ids": dimension_mismatch_chunk_ids,
    }
    base_status["ok"] = (
        not base_status["errors"]
        and payloadless_points == 0
        and not duplicate_chunk_ids
        and all(not values for values in base_status["drift"].values())
    )
    return base_status


def delete_wiki_rag_orphaned_points(
    *,
    status: dict[str, Any],
    qdrant_url: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    collection = str(status["collection"])
    effective_qdrant_url = (qdrant_url or status.get("qdrant_url") or os.getenv("QDRANT_URL", "http://127.0.0.1:6333")).rstrip("/")
    orphaned_chunk_ids = set(status.get("drift", {}).get("orphaned_chunk_ids", []))
    if not orphaned_chunk_ids:
        return {"deleted_count": 0, "deleted_chunk_ids": []}
    indexed_points = _scroll_collection_points(
        qdrant_url=effective_qdrant_url,
        collection=collection,
        timeout=timeout,
    )
    point_ids: list[Any] = []
    deleted_chunk_ids: list[str] = []
    for point in indexed_points:
        payload = point.get("payload")
        if not isinstance(payload, dict):
            continue
        chunk_id = payload.get("chunk_id")
        if chunk_id in orphaned_chunk_ids:
            point_ids.append(point.get("id"))
            deleted_chunk_ids.append(chunk_id)
    point_ids = [point_id for point_id in point_ids if point_id is not None]
    if point_ids:
        _delete_points(
            qdrant_url=effective_qdrant_url,
            collection=collection,
            point_ids=point_ids,
            timeout=timeout,
        )
    return {
        "deleted_count": len(point_ids),
        "deleted_chunk_ids": sorted(deleted_chunk_ids),
    }


def _selected_pages(store: WikiStore, categories: set[str]) -> list[WikiPage]:
    pages = []
    for page_name in sorted(store.allowed_page_names()):
        if page_name == "log.md":
            continue
        page = store.read_page(page_name)
        if store.page_category(page.name) in categories:
            pages.append(page)
    return pages


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


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part)[:80] or "section"


def _page_path(store: WikiStore, page_name: str) -> str:
    normalized = store.normalize_page_name(page_name)
    if normalized == "index.md":
        return str(store.index_path.relative_to(store.root))
    if normalized == "log.md":
        return str(store.log_path.relative_to(store.root))
    if normalized in store.root_docs:
        return str(store.root_docs[normalized].relative_to(store.root))
    return str((store.guidance_dir / normalized).relative_to(store.root))


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


def _qdrant_headers() -> dict[str, str]:
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if qdrant_api_key:
        return {"api-key": qdrant_api_key}
    return {}


def _get_collection_info(*, qdrant_url: str, collection: str, timeout: float) -> dict[str, Any]:
    return _http_json(
        method="GET",
        url=f"{qdrant_url.rstrip('/')}/collections/{collection}",
        headers=_qdrant_headers(),
        timeout=timeout,
    )


def _scroll_collection_points(
    *,
    qdrant_url: str,
    collection: str,
    timeout: float,
    limit: int = 256,
) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    offset: Any | None = None
    while True:
        payload: dict[str, Any] = {
            "limit": limit,
            "with_payload": STATUS_PAYLOAD_FIELDS,
            "with_vector": False,
        }
        if offset is not None:
            payload["offset"] = offset
        data = _http_json(
            method="POST",
            url=f"{qdrant_url.rstrip('/')}/collections/{collection}/points/scroll",
            payload=payload,
            headers=_qdrant_headers(),
            timeout=timeout,
        )
        result = data.get("result", {})
        page_points = result.get("points", [])
        if not isinstance(page_points, list):
            raise QdrantAskError("Qdrant scroll response did not include a points list")
        points.extend(point for point in page_points if isinstance(point, dict))
        offset = result.get("next_page_offset")
        if offset is None:
            break
    return points


def _delete_points(
    *,
    qdrant_url: str,
    collection: str,
    point_ids: list[Any],
    timeout: float,
) -> None:
    _http_json(
        method="POST",
        url=f"{qdrant_url.rstrip('/')}/collections/{collection}/points/delete?wait=true",
        payload={"points": point_ids},
        headers=_qdrant_headers(),
        timeout=timeout,
    )


def _points_count(collection_info: dict[str, Any]) -> int | None:
    result = collection_info.get("result")
    if not isinstance(result, dict):
        return None
    value = result.get("points_count")
    return value if isinstance(value, int) else None
