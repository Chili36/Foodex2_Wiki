from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
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

from scripts.index_wiki_qdrant import (  # noqa: E402
    DEFAULT_DIMENSION,
    DEFAULT_MODEL,
    _http_json,
)
from wiki_api.librarian import AnthropicFoodEx2Answerer  # noqa: E402


WIKI_COLLECTION = "foodex2_wiki_markdown_v1"
SOURCE_COLLECTION = "foodex2_source_docs_v1"


def _ssl_context() -> ssl.SSLContext | None:
    return ssl.create_default_context(cafile=certifi.where()) if certifi else None


def _post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part)[:100] or "question"


def _query_embedding(
    *,
    query: str,
    model: str,
    dimension: int,
    timeout: float,
) -> tuple[list[float], dict[str, Any], int]:
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY is not set")
    started = time.perf_counter()
    payload = {
        "inputs": [[query]],
        "input_type": "query",
        "model": model,
        "output_dimension": dimension,
        "output_dtype": "float",
    }
    req = request.Request(
        "https://api.voyageai.com/v1/contextualizedembeddings",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
        data = json.loads(response.read().decode("utf-8"))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return data["data"][0]["data"][0]["embedding"], data.get("usage", {}), elapsed_ms


def _known_embedding_tokens(usage: dict[str, Any]) -> int | None:
    value = usage.get("total_tokens") or usage.get("totalTokens") or usage.get("total")
    return value if isinstance(value, int) else None


def _run_markdown_ask(
    *,
    question: str,
    ask_url: str,
    max_pages: int,
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "question": question,
        "max_pages": max_pages,
        "include_page_content": False,
        "use_graph_expansion": False,
    }
    started = time.perf_counter()
    status_code, response_data = _post_json(ask_url, payload, timeout)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "mode": "normal_markdown_ask",
        "question": question,
        "status_code": status_code,
        "elapsed_ms": elapsed_ms,
        "request_payload": payload,
        "response": response_data,
    }


def _qdrant_payload_fields(collection: str) -> list[str]:
    if collection == SOURCE_COLLECTION:
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
        "content",
    ]


def _format_qdrant_pages(collection: str, results: list[dict[str, Any]]) -> list[dict[str, str]]:
    pages = []
    for item in results:
        payload = item.get("payload", {})
        score = item.get("score")
        if collection == SOURCE_COLLECTION:
            source_file = payload.get("source_file") or "source-result"
            location = payload.get("location") or ""
            content = (
                f"Qdrant score: {score}\n"
                f"Source file: {source_file}\n"
                f"Source path: {payload.get('source_path')}\n"
                f"Format: {payload.get('source_suffix')}\n"
                f"Location: {location}\n\n"
                f"{payload.get('content', '')}"
            )
            pages.append({"page_name": f"{source_file} :: {location}", "content": content})
        else:
            page_name = payload.get("page_name") or "wiki-result"
            heading = payload.get("heading_path") or ""
            content = (
                f"Qdrant score: {score}\n"
                f"Page: {payload.get('title')}\n"
                f"File: {page_name}\n"
                f"Category: {payload.get('category')}\n"
                f"Section: {heading}\n"
                f"Summary: {payload.get('summary')}\n\n"
                f"{payload.get('content', '')}"
            )
            pages.append({"page_name": f"{page_name} :: {heading}", "content": content})
    return pages


def _compact_result_metadata(collection: str, item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload", {})
    if collection == SOURCE_COLLECTION:
        return {
            "score": item.get("score"),
            "source_file": payload.get("source_file"),
            "source_path": payload.get("source_path"),
            "location": payload.get("location"),
            "source_suffix": payload.get("source_suffix"),
        }
    return {
        "score": item.get("score"),
        "page_name": payload.get("page_name"),
        "heading_path": payload.get("heading_path"),
        "category": payload.get("category"),
        "summary": payload.get("summary"),
    }


def _run_qdrant_ask(
    *,
    question: str,
    qdrant_url: str,
    collection: str,
    limit: int,
    answerer_model: str,
    embedding_model: str,
    embedding_dimension: int,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    vector, usage, embed_ms = _query_embedding(
        query=question,
        model=embedding_model,
        dimension=embedding_dimension,
        timeout=timeout,
    )
    search_started = time.perf_counter()
    search_response = _http_json(
        method="POST",
        url=f"{qdrant_url.rstrip('/')}/collections/{collection}/points/search",
        payload={
            "vector": vector,
            "limit": limit,
            "with_payload": _qdrant_payload_fields(collection),
            "with_vector": False,
        },
        timeout=timeout,
    )
    search_ms = int((time.perf_counter() - search_started) * 1000)
    results = search_response.get("result", [])
    answerer_started = time.perf_counter()
    answerer = AnthropicFoodEx2Answerer(model=answerer_model)
    answer_result = answerer.run(
        question=question,
        pages=_format_qdrant_pages(collection, results),
    )
    answerer_ms = int((time.perf_counter() - answerer_started) * 1000)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    embedding_tokens = _known_embedding_tokens(usage)
    answerer_tokens = answer_result.token_summary.get("total_tracked_tokens")
    combined_tokens = answerer_tokens or 0
    if embedding_tokens is not None:
        combined_tokens += embedding_tokens
    return {
        "mode": "qdrant_ask_emulation",
        "question": question,
        "retrieval_collection": collection,
        "elapsed_ms": elapsed_ms,
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
            "collection": collection,
            "elapsed_ms": search_ms,
            "limit": limit,
            "results": [_compact_result_metadata(collection, item) for item in results],
        },
        "answerer": {
            "model": answerer.model,
            "elapsed_ms": answerer_ms,
            "token_summary": answer_result.token_summary,
            "timing_summary": answer_result.timing_summary,
        },
        "total": {
            "elapsed_ms": elapsed_ms,
            "llm_calls": 1,
            "answerer_tracked_tokens": answerer_tokens,
            "embedding_tracked_tokens": embedding_tokens,
            "combined_known_tokens": combined_tokens,
        },
        "answer": answer_result.answer,
        "citations": answer_result.citations,
    }


def _summary_for_result(result: dict[str, Any]) -> dict[str, Any]:
    if result["mode"] == "normal_markdown_ask":
        response = result.get("response", {})
        trace = response.get("trace", {}) if isinstance(response, dict) else {}
        return {
            "mode": result["mode"],
            "status_code": result.get("status_code"),
            "elapsed_ms": result.get("elapsed_ms"),
            "trace_total_ms": trace.get("total", {}).get("request_wall_time_ms"),
            "total_tokens": trace.get("total", {}).get("total_tracked_tokens"),
            "retrieval_tokens": trace.get("retrieval", {})
            .get("token_summary", {})
            .get("total_tracked_tokens"),
            "answerer_tokens": trace.get("answerer", {})
            .get("token_summary", {})
            .get("total_tracked_tokens"),
            "llm_calls": trace.get("total", {}).get("total_llm_calls"),
            "pages_used": response.get("pages_used", []),
            "citations": response.get("citations", []),
        }
    return {
        "mode": result["mode"],
        "collection": result.get("retrieval_collection"),
        "elapsed_ms": result.get("elapsed_ms"),
        "total_tokens": result.get("total", {}).get("combined_known_tokens"),
        "answerer_tokens": result.get("total", {}).get("answerer_tracked_tokens"),
        "embedding_tokens": result.get("total", {}).get("embedding_tracked_tokens"),
        "llm_calls": result.get("total", {}).get("llm_calls"),
        "results": result.get("retrieval", {}).get("results", []),
        "citations": result.get("citations", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run normal /wiki/ask and Qdrant-backed ask emulations for one or more questions."
    )
    parser.add_argument("questions", nargs="+")
    parser.add_argument("--ask-url", default="http://127.0.0.1:8010/wiki/ask")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    parser.add_argument("--answerer-model", default="")
    parser.add_argument("--embedding-model", default=os.getenv("WIKI_EMBED_MODEL", DEFAULT_MODEL))
    parser.add_argument("--embedding-dimension", type=int, default=int(os.getenv("WIKI_EMBED_DIMENSION", DEFAULT_DIMENSION)))
    parser.add_argument("--max-pages", type=int, default=7)
    parser.add_argument("--qdrant-limit", type=int, default=7)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "reports" / "retrieval-ab")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    answerer_model = (
        args.answerer_model
        or os.getenv("WIKI_ANSWERER_MODEL")
        or os.getenv("WIKI_LIBRARIAN_MODEL")
        or "claude-sonnet-4-6"
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_runs = []
    for question in args.questions:
        question_slug = _slug(question)
        runs = [
            _run_markdown_ask(
                question=question,
                ask_url=args.ask_url,
                max_pages=args.max_pages,
                timeout=args.timeout,
            ),
            _run_qdrant_ask(
                question=question,
                qdrant_url=args.qdrant_url,
                collection=WIKI_COLLECTION,
                limit=args.qdrant_limit,
                answerer_model=answerer_model,
                embedding_model=args.embedding_model,
                embedding_dimension=args.embedding_dimension,
                timeout=args.timeout,
            ),
            _run_qdrant_ask(
                question=question,
                qdrant_url=args.qdrant_url,
                collection=SOURCE_COLLECTION,
                limit=args.qdrant_limit,
                answerer_model=answerer_model,
                embedding_model=args.embedding_model,
                embedding_dimension=args.embedding_dimension,
                timeout=args.timeout,
            ),
        ]
        question_output = {
            "question": question,
            "answerer_model": answerer_model,
            "embedding_model": args.embedding_model,
            "embedding_dimension": args.embedding_dimension,
            "runs": runs,
            "summary": [_summary_for_result(result) for result in runs],
        }
        output_path = args.output_dir / f"{question_slug}.json"
        output_path.write_text(json.dumps(question_output, indent=2, ensure_ascii=False) + "\n")
        all_runs.append({"question": question, "output_path": str(output_path), "summary": question_output["summary"]})
        print(json.dumps(all_runs[-1], indent=2, ensure_ascii=False), flush=True)

    combined_path = args.output_dir / "latest-comparison.json"
    combined_path.write_text(json.dumps(all_runs, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote combined summary to {combined_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
