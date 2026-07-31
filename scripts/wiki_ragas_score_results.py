"""Add Ragas judge metrics to an existing wiki endpoint evaluation.

This scores the answers and contexts already captured in a results.json file.
It deliberately does not rerun retrieval, page selection, or answer generation,
so stochastic endpoint behavior cannot change the evidence being judged.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from scripts.wiki_ragas_eval import (
        REPO_ROOT,
        SUPPORTED_METRICS,
        create_judge_llm,
        load_cases,
        score_with_ragas,
        split_csv,
        summarize,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    from wiki_ragas_eval import (  # type: ignore[no-redef]
        REPO_ROOT,
        SUPPORTED_METRICS,
        create_judge_llm,
        load_cases,
        score_with_ragas,
        split_csv,
        summarize,
    )


async def score_rows(
    *,
    rows: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    metric_names: list[str],
    judge_llm: Any,
    concurrency: int,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def score_row(row: dict[str, Any]) -> dict[str, Any]:
        scored = dict(row)
        scored["ragas"] = dict(row.get("ragas") or {})
        if row.get("status_code") != 200:
            return scored
        case = cases_by_id.get(str(row.get("case_id")))
        if case is None:
            scored["ragas"]["_error"] = {
                "error": f"case not found in dataset: {row.get('case_id')}"
            }
            return scored
        async with semaphore:
            scored["ragas"].update(
                await score_with_ragas(
                    case=case,
                    response={
                        "answer": row.get("answer", ""),
                        "pages": row.get("pages", []),
                    },
                    metric_names=metric_names,
                    judge_llm=judge_llm,
                )
            )
        return scored

    tasks = [asyncio.create_task(score_row(row)) for row in rows]
    scored_rows: list[dict[str, Any]] = []
    for completed, task in enumerate(asyncio.as_completed(tasks), start=1):
        scored_rows.append(await task)
        print(f"scored {completed}/{len(tasks)} rows", flush=True)

    order = {
        (
            row.get("repeat"),
            row.get("case_id"),
            row.get("answerer_model"),
            row.get("endpoint"),
        ): index
        for index, row in enumerate(rows)
    }
    scored_rows.sort(
        key=lambda row: order[
            (
                row.get("repeat"),
                row.get("case_id"),
                row.get("answerer_model"),
                row.get("endpoint"),
            )
        ]
    )
    return scored_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-results", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--metrics", default="faithfulness")
    parser.add_argument(
        "--answerer-models",
        default="",
        help="Optional comma-separated model filter for a multi-model result file.",
    )
    parser.add_argument("--judge-model", default="claude-sonnet-4-6")
    parser.add_argument(
        "--judge-provider",
        choices=["auto", "anthropic", "openai", "lmstudio"],
        default="auto",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    metrics = split_csv(args.metrics)
    invalid_metrics = sorted(set(metrics) - SUPPORTED_METRICS)
    if invalid_metrics or not metrics:
        parser.error(f"unsupported metrics: {invalid_metrics or metrics}")

    load_dotenv(REPO_ROOT / ".env")
    input_path = (
        args.input_results
        if args.input_results.is_absolute()
        else REPO_ROOT / args.input_results
    )
    cases_path = args.cases if args.cases.is_absolute() else REPO_ROOT / args.cases
    try:
        source_result = json.loads(input_path.read_text())
        cases = load_cases(cases_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    rows = source_result.get("rows")
    if not isinstance(rows, list):
        parser.error("input results must contain a top-level rows list")
    requested_models = set(split_csv(args.answerer_models))
    if requested_models:
        available_models = {
            str(row.get("answerer_model"))
            for row in rows
            if row.get("answerer_model")
        }
        missing_models = sorted(requested_models - available_models)
        if missing_models:
            parser.error(f"models not found in input results: {missing_models}")
        rows = [
            row for row in rows if row.get("answerer_model") in requested_models
        ]

    try:
        judge_llm = create_judge_llm(args.judge_model, args.judge_provider)
    except (ImportError, ValueError) as exc:
        parser.error(f"cannot initialize Ragas judge: {exc}")

    cases_by_id = {case["id"]: case for case in cases}
    scored_rows = asyncio.run(
        score_rows(
            rows=rows,
            cases_by_id=cases_by_id,
            metric_names=metrics,
            judge_llm=judge_llm,
            concurrency=args.concurrency,
        )
    )
    configuration = dict(source_result.get("configuration") or {})
    configuration.update(
        {
            "ragas_metrics": metrics,
            "judge_model": args.judge_model,
            "judge_provider": args.judge_provider,
            "scored_from_results": str(input_path),
            "judge_concurrency": args.concurrency,
        }
    )
    result = {
        **source_result,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dataset": str(cases_path),
        "configuration": configuration,
        "summary": summarize(scored_rows),
        "rows": scored_rows,
    }
    output_dir = (
        REPO_ROOT
        / "reports"
        / "wiki-ragas-evals"
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "results.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
