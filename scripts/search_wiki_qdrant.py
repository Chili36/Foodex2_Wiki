from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.index_wiki_qdrant import (  # noqa: E402
    DEFAULT_COLLECTION,
    DEFAULT_DIMENSION,
    DEFAULT_MODEL,
    _http_json,
    _voyage_context_embed,
)


def _query_vector(*, query: str, model: str, dimension: int, timeout: float) -> list[float]:
    embedded = _voyage_context_embed(
        documents=[[query]],
        input_type="query",
        model=model,
        dimension=dimension,
        timeout=timeout,
    )
    if len(embedded) != 1 or len(embedded[0]) != 1:
        raise RuntimeError("Voyage returned an unexpected query embedding shape")
    return embedded[0][0]


def _make_filter(category: str | None) -> dict[str, Any] | None:
    if not category:
        return None
    return {"must": [{"key": "category", "match": {"value": category}}]}


def _excerpt(content: str, max_chars: int = 420) -> str:
    collapsed = " ".join(content.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[: max_chars - 1].rstrip() + "..."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe the local Qdrant index built from the FoodEx2 markdown wiki."
    )
    parser.add_argument("query")
    parser.add_argument("--collection", default=os.getenv("WIKI_QDRANT_COLLECTION", DEFAULT_COLLECTION))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"))
    parser.add_argument("--model", default=os.getenv("WIKI_EMBED_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dimension", type=int, default=int(os.getenv("WIKI_EMBED_DIMENSION", DEFAULT_DIMENSION)))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--category")
    parser.add_argument("--json", action="store_true", help="Return raw compact JSON.")
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    qdrant_url = args.qdrant_url.rstrip("/")
    vector = _query_vector(
        query=args.query,
        model=args.model,
        dimension=args.dimension,
        timeout=args.timeout,
    )
    payload: dict[str, Any] = {
        "vector": vector,
        "limit": args.limit,
        "with_payload": [
            "page_name",
            "title",
            "category",
            "heading_path",
            "summary",
            "source_file",
            "source_suffix",
            "source_path",
            "location",
            "content",
        ],
        "with_vector": False,
    }
    query_filter = _make_filter(args.category)
    if query_filter:
        payload["filter"] = query_filter

    response = _http_json(
        method="POST",
        url=f"{qdrant_url}/collections/{args.collection}/points/search",
        payload=payload,
        timeout=args.timeout,
    )
    results = response.get("result", [])
    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    for index, item in enumerate(results, start=1):
        point_payload = item.get("payload", {})
        name = point_payload.get("page_name") or point_payload.get("source_file")
        location = point_payload.get("heading_path") or point_payload.get("location")
        kind = point_payload.get("category") or point_payload.get("source_suffix")
        summary = point_payload.get("summary") or point_payload.get("source_path")
        print(
            f"{index}. score={item.get('score'):.4f} "
            f"{name} | {location}"
        )
        print(f"   category: {kind}")
        print(f"   summary: {summary}")
        print(f"   excerpt: {_excerpt(point_payload.get('content', ''))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
