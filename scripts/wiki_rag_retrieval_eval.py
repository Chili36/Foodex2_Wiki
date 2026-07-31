"""Evaluate wiki-mode Qdrant retrieval without invoking an answerer."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
import sys
import time
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.qdrant_ask import retrieve_qdrant_ask_context  # noqa: E402
from wiki_api.rag_scoring import (  # noqa: E402
    aggregate_retrieval_scores,
    score_retrieval_case,
)

DEFAULT_MAX_ESTIMATED_CALLS = 200


def _run_case(
    case: dict[str, Any],
    *,
    limit: int,
    candidate_limit: int | None,
    strategy: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    context = retrieve_qdrant_ask_context(
        question=case["question"],
        retrieval_mode="wiki",
        limit=limit,
        candidate_limit=candidate_limit,
        retrieval_strategy=strategy,
    )
    wall_ms = int((time.perf_counter() - started) * 1000)
    retrieval = context["retrieval"]
    raw_pages = [
        result["page_name"]
        for result in retrieval.get("results", [])
        if isinstance(result.get("page_name"), str)
    ]
    score = score_retrieval_case(
        labels=case["labels"],
        raw_page_names=raw_pages,
        final_page_names=context["pages_used"],
        requested_page_limit=limit,
    )
    embedding_ms = context["embedding"].get("elapsed_ms")
    qdrant_ms = retrieval.get("elapsed_ms")
    assembly_ms = (retrieval.get("assembly") or {}).get("elapsed_ms")
    phase_values = [
        value
        for value in (embedding_ms, qdrant_ms, assembly_ms)
        if isinstance(value, (int, float))
    ]
    return {
        "id": case["id"],
        "reviewed": bool(case.get("reviewed")),
        "question": case["question"],
        "context": case.get("context", {}),
        "raw_candidate_pages": raw_pages,
        "pages_used": context["pages_used"],
        "retrieval_ms": sum(phase_values),
        "request_wall_time_ms": wall_ms,
        "embedding": context["embedding"],
        "retrieval": retrieval,
        **score,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold-path",
        default="evals/wiki-rag/retrieval_cases.json",
    )
    parser.add_argument("--label", required=True)
    parser.add_argument("--limit", type=int, default=7)
    parser.add_argument("--candidate-limit", type=int, default=None)
    parser.add_argument(
        "--strategy",
        choices=["legacy_topk", "diverse_pages"],
        default="diverse_pages",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--only-reviewed", action="store_true")
    parser.add_argument(
        "--max-estimated-calls",
        type=int,
        default=DEFAULT_MAX_ESTIMATED_CALLS,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.candidate_limit is not None and args.candidate_limit < args.limit:
        parser.error("--candidate-limit must be at least --limit")
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    load_dotenv(REPO_ROOT / ".env")
    gold = json.loads((REPO_ROOT / args.gold_path).read_text())
    cases = [
        case
        for case in gold["cases"]
        if case.get("reviewed") or not args.only_reviewed
    ]
    estimated_calls = len(cases) * args.repeats
    if estimated_calls > args.max_estimated_calls:
        parser.error(
            f"estimated {estimated_calls} embedding calls exceeds "
            f"--max-estimated-calls {args.max_estimated_calls}"
        )
    budget = {
        "cases": len(cases),
        "repeats": args.repeats,
        "estimated_embedding_calls": estimated_calls,
        "limit": args.limit,
        "candidate_limit": args.candidate_limit,
        "strategy": args.strategy,
    }
    print("EVAL BUDGET:", json.dumps(budget, indent=2))
    if args.dry_run:
        return 0

    passes = []
    for pass_number in range(1, args.repeats + 1):
        rows = []
        for case in cases:
            row = _run_case(
                case,
                limit=args.limit,
                candidate_limit=args.candidate_limit,
                strategy=args.strategy,
            )
            rows.append(row)
            print(
                f"[pass {pass_number}] {row['id']}: "
                f"recall={row['must_have_recall']:.2f} "
                f"unique={row['final_unique_page_count']} "
                f"preassembly_waste="
                f"{row['preassembly_duplicate_slot_waste']:.2f} "
                f"final_waste={row['duplicate_slot_waste']:.2f} "
                f"leaks={row['leaks']}",
                flush=True,
            )
        passes.append(
            {
                "summary": aggregate_retrieval_scores(rows),
                "cases": rows,
            }
        )

    metric_names = list(passes[0]["summary"]) if passes else []
    medians = {
        metric: statistics.median(
            pass_result["summary"][metric] for pass_result in passes
        )
        for metric in metric_names
        if metric != "case_count"
    }
    result = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gold_path": args.gold_path,
        "budget": budget,
        "passes": passes,
        "median_summary": medians,
    }
    out_dir = (
        REPO_ROOT
        / "reports"
        / "wiki-rag-evals"
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "retrieval-results.json"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print("MEDIAN SUMMARY:", json.dumps(medians, indent=2))
    print("wrote", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
