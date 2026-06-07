from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.rag_index import (  # noqa: E402
    DEFAULT_WIKI_CATEGORIES,
    DEFAULT_WIKI_CHUNK_MAX_CHARS,
    build_wiki_rag_manifest,
    delete_wiki_rag_orphaned_points,
    get_wiki_rag_status,
)
from wiki_api.wiki_store import WikiStore  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check deterministic drift between markdown wiki pages and the Qdrant wiki RAG index."
    )
    parser.add_argument("--collection", default=os.getenv("WIKI_QDRANT_COLLECTION"))
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL"))
    parser.add_argument("--embedding-model", default=os.getenv("WIKI_EMBED_MODEL"))
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=None,
    )
    parser.add_argument("--categories", default=DEFAULT_WIKI_CATEGORIES)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_WIKI_CHUNK_MAX_CHARS)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Print the expected markdown-derived manifest without contacting Qdrant.",
    )
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help="Delete Qdrant points whose chunk ids no longer exist in the markdown-derived index.",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    if args.manifest_only:
        embedding_dimension = args.embedding_dimension or int(os.getenv("WIKI_EMBED_DIMENSION", "1024"))
        print(
            json.dumps(
                build_wiki_rag_manifest(
                    store=WikiStore(REPO_ROOT),
                    collection=args.collection or os.getenv("WIKI_QDRANT_COLLECTION") or "foodex2_wiki_markdown_v1",
                    embedding_model=args.embedding_model or os.getenv("WIKI_EMBED_MODEL") or "voyage-context-3",
                    embedding_dimension=embedding_dimension,
                    categories=args.categories,
                    max_chars=args.max_chars,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    status = get_wiki_rag_status(
        root=REPO_ROOT,
        collection=args.collection,
        qdrant_url=args.qdrant_url,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
        categories=args.categories,
        max_chars=args.max_chars,
        timeout=args.timeout,
    )
    if args.delete_orphans:
        delete_result = delete_wiki_rag_orphaned_points(
            status=status,
            qdrant_url=args.qdrant_url,
            timeout=args.timeout,
        )
        status = get_wiki_rag_status(
            root=REPO_ROOT,
            collection=args.collection,
            qdrant_url=args.qdrant_url,
            embedding_model=args.embedding_model,
            embedding_dimension=args.embedding_dimension,
            categories=args.categories,
            max_chars=args.max_chars,
            timeout=args.timeout,
        )
        status["orphan_delete"] = delete_result
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
