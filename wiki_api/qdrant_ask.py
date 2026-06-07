from __future__ import annotations

import json
import os
import ssl
import time
from typing import Any, Literal
from urllib import error, request

try:
    import certifi
except ImportError:  # pragma: no cover - certifi is installed with common HTTP clients.
    certifi = None


DEFAULT_EMBEDDING_DIMENSION = 1024
DEFAULT_EMBEDDING_MODEL = "voyage-context-3"
DEFAULT_SOURCE_COLLECTION = "foodex2_source_docs_v1"
DEFAULT_WIKI_COLLECTION = "foodex2_wiki_markdown_v1"


class QdrantAskError(RuntimeError):
    """Raised when the Qdrant-backed ask path cannot retrieve context."""


def _ssl_context() -> ssl.SSLContext | None:
    return ssl.create_default_context(cafile=certifi.where()) if certifi else None


def _http_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    req = request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise QdrantAskError(f"{url} returned HTTP {exc.code}: {raw[:800]}") from exc
    except error.URLError as exc:
        raise QdrantAskError(f"{url} could not be reached: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise QdrantAskError(f"{url} returned non-JSON data") from exc


def _known_embedding_tokens(usage: dict[str, Any]) -> int | None:
    value = usage.get("total_tokens") or usage.get("totalTokens") or usage.get("total")
    return value if isinstance(value, int) else None


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise QdrantAskError(f"{name} must be an integer, got {value!r}") from exc


def default_collection(retrieval_mode: Literal["wiki", "source"]) -> str:
    if retrieval_mode == "source":
        return os.getenv("SOURCE_QDRANT_COLLECTION", DEFAULT_SOURCE_COLLECTION)
    return os.getenv("WIKI_QDRANT_COLLECTION", DEFAULT_WIKI_COLLECTION)


def default_embedding_model(retrieval_mode: Literal["wiki", "source"]) -> str:
    if retrieval_mode == "source":
        return os.getenv("SOURCE_EMBED_MODEL") or os.getenv("WIKI_EMBED_MODEL") or DEFAULT_EMBEDDING_MODEL
    return os.getenv("WIKI_EMBED_MODEL", DEFAULT_EMBEDDING_MODEL)


def default_embedding_dimension(retrieval_mode: Literal["wiki", "source"]) -> int:
    if retrieval_mode == "source":
        if os.getenv("SOURCE_EMBED_DIMENSION") is not None:
            return _env_int("SOURCE_EMBED_DIMENSION", DEFAULT_EMBEDDING_DIMENSION)
        return _env_int("WIKI_EMBED_DIMENSION", DEFAULT_EMBEDDING_DIMENSION)
    return _env_int("WIKI_EMBED_DIMENSION", DEFAULT_EMBEDDING_DIMENSION)


def _payload_fields(retrieval_mode: Literal["wiki", "source"]) -> list[str]:
    if retrieval_mode == "source":
        return [
            "source_file",
            "source_suffix",
            "source_path",
            "location",
            "page_number",
            "content",
        ]
    return [
        "page_name",
        "title",
        "category",
        "heading_path",
        "summary",
        "source_path",
        "sources",
        "related",
        "content",
    ]


def _query_embedding(
    *,
    query: str,
    model: str,
    dimension: int,
    timeout: float,
) -> tuple[list[float], dict[str, Any], int]:
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise QdrantAskError("VOYAGE_API_KEY is not set")
    started = time.perf_counter()
    data = _http_json(
        method="POST",
        url="https://api.voyageai.com/v1/contextualizedembeddings",
        payload={
            "inputs": [[query]],
            "input_type": "query",
            "model": model,
            "output_dimension": dimension,
            "output_dtype": "float",
        },
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=timeout,
    )
    try:
        vector = data["data"][0]["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise QdrantAskError("Voyage embedding response did not include an embedding") from exc
    if not isinstance(vector, list):
        raise QdrantAskError("Voyage embedding response did not include a vector list")
    return vector, data.get("usage", {}), int((time.perf_counter() - started) * 1000)


def _search_qdrant(
    *,
    qdrant_url: str,
    collection: str,
    retrieval_mode: Literal["wiki", "source"],
    vector: list[float],
    limit: int,
    timeout: float,
) -> tuple[list[dict[str, Any]], int]:
    headers: dict[str, str] = {}
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if qdrant_api_key:
        headers["api-key"] = qdrant_api_key
    started = time.perf_counter()
    data = _http_json(
        method="POST",
        url=f"{qdrant_url.rstrip('/')}/collections/{collection}/points/search",
        payload={
            "vector": vector,
            "limit": limit,
            "with_payload": _payload_fields(retrieval_mode),
            "with_vector": False,
        },
        headers=headers,
        timeout=timeout,
    )
    results = data.get("result", [])
    if not isinstance(results, list):
        raise QdrantAskError("Qdrant search response did not include a result list")
    return results, int((time.perf_counter() - started) * 1000)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _format_wiki_result(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload", {})
    page_name = str(payload.get("page_name") or "wiki-result")
    title = str(payload.get("title") or page_name)
    heading = str(payload.get("heading_path") or "")
    score = item.get("score")
    content = (
        f"Qdrant score: {score}\n"
        f"Page: {title}\n"
        f"File: {page_name}\n"
        f"Category: {payload.get('category')}\n"
        f"Section: {heading}\n"
        f"Summary: {payload.get('summary')}\n\n"
        f"{payload.get('content', '')}"
    )
    return {
        "answerer_page": {"page_name": page_name, "content": content},
        "page_summary": {
            "page_name": page_name,
            "title": title,
            "summary": str(payload.get("summary") or ""),
            "category": payload.get("category"),
            "sources": payload.get("sources") if isinstance(payload.get("sources"), list) else [],
            "related": payload.get("related") if isinstance(payload.get("related"), list) else [],
            "content": content,
        },
        "pages_used": page_name,
        "metadata": {
            "score": score,
            "page_name": page_name,
            "heading_path": heading,
            "category": payload.get("category"),
            "summary": payload.get("summary"),
            "source_path": payload.get("source_path"),
        },
    }


def _format_source_result(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload", {})
    source_file = str(payload.get("source_file") or "source-result")
    location = str(payload.get("location") or "")
    score = item.get("score")
    title = f"{source_file} :: {location}" if location else source_file
    content = (
        f"Qdrant score: {score}\n"
        f"Source file: {source_file}\n"
        f"Source path: {payload.get('source_path')}\n"
        f"Format: {payload.get('source_suffix')}\n"
        f"Location: {location}\n\n"
        f"{payload.get('content', '')}"
    )
    return {
        "answerer_page": {"page_name": source_file, "content": content},
        "page_summary": {
            "page_name": source_file,
            "title": title,
            "summary": str(payload.get("source_path") or location or source_file),
            "category": "source_document",
            "sources": [str(payload.get("source_path"))] if payload.get("source_path") else [],
            "related": [],
            "content": content,
        },
        "pages_used": source_file,
        "metadata": {
            "score": score,
            "source_file": source_file,
            "source_path": payload.get("source_path"),
            "location": location,
            "page_number": payload.get("page_number"),
            "source_suffix": payload.get("source_suffix"),
        },
    }


def retrieve_qdrant_ask_context(
    *,
    question: str,
    retrieval_mode: Literal["wiki", "source"],
    collection: str | None = None,
    limit: int = 7,
    qdrant_url: str | None = None,
    embedding_model: str | None = None,
    embedding_dimension: int | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    collection = collection or default_collection(retrieval_mode)
    embedding_model = embedding_model or default_embedding_model(retrieval_mode)
    embedding_dimension = embedding_dimension or default_embedding_dimension(retrieval_mode)

    vector, usage, embed_ms = _query_embedding(
        query=question,
        model=embedding_model,
        dimension=embedding_dimension,
        timeout=timeout,
    )
    results, search_ms = _search_qdrant(
        qdrant_url=qdrant_url,
        collection=collection,
        retrieval_mode=retrieval_mode,
        vector=vector,
        limit=limit,
        timeout=timeout,
    )

    formatter = _format_source_result if retrieval_mode == "source" else _format_wiki_result
    formatted = [formatter(item) for item in results]
    embedding_tokens = _known_embedding_tokens(usage)
    return {
        "answerer_pages": [item["answerer_page"] for item in formatted],
        "page_summaries": [item["page_summary"] for item in formatted],
        "pages_used": _dedupe([item["pages_used"] for item in formatted]),
        "embedding": {
            "provider": "voyage",
            "model": embedding_model,
            "dimension": embedding_dimension,
            "elapsed_ms": embed_ms,
            "usage": usage,
            "tracked_tokens": embedding_tokens,
        },
        "retrieval": {
            "provider": "qdrant",
            "retrieval_mode": retrieval_mode,
            "collection": collection,
            "qdrant_url": qdrant_url,
            "elapsed_ms": search_ms,
            "limit": limit,
            "result_count": len(results),
            "results": [item["metadata"] for item in formatted],
        },
    }
