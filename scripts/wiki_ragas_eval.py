"""Compare /wiki/ask and /wiki/ask-rag across answer models.

The runner keeps deterministic DMT assertions separate from optional
Ragas LLM-as-judge metrics. It always requests page content so faithfulness
and retrieval metrics are scored against the context actually sent back by
the endpoint.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import fnmatch
import json
import os
import socket
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENDPOINTS = ("ask", "ask-rag")
DEFAULT_METRICS = ("answer_accuracy", "faithfulness")
SUPPORTED_METRICS = {
    "answer_accuracy",
    "faithfulness",
    "factual_correctness",
    "context_precision",
    "context_recall",
    "rubric",
}
RUBRIC_KEYS = {f"score{score}_description" for score in range(1, 6)}


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def load_cases(path: Path, *, only_reviewed: bool = False) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("dataset must contain a top-level 'cases' list")

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"case {index} must be an object")
        case_id = case.get("id")
        question = case.get("question")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"case {index} needs a non-empty string id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"{case_id} needs a non-empty question")
        seen_ids.add(case_id)

        for field in (
            "reference_pages",
            "acceptable_pages",
            "must_not_pages",
            "required_answer_terms",
            "forbidden_answer_terms",
        ):
            value = case.get(field, [])
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ValueError(f"{case_id}.{field} must be a list of non-empty strings")
        reference = case.get("reference_answer")
        if reference is not None and (
            not isinstance(reference, str) or not reference.strip()
        ):
            raise ValueError(f"{case_id}.reference_answer must be a non-empty string")
        for field in ("source", "domain", "shape", "request_question"):
            value = case.get(field)
            if value is not None and (
                not isinstance(value, str) or not value.strip()
            ):
                raise ValueError(f"{case_id}.{field} must be a non-empty string")
        rubric = case.get("rubric")
        if rubric is not None and (
            not isinstance(rubric, dict)
            or not all(
                isinstance(key, str)
                and isinstance(value, str)
                and value.strip()
                for key, value in rubric.items()
            )
        ):
            raise ValueError(f"{case_id}.rubric must map strings to non-empty strings")
        if rubric is not None and set(rubric) != RUBRIC_KEYS:
            raise ValueError(
                f"{case_id}.rubric must define score1_description through "
                "score5_description"
            )

        if only_reviewed and not case.get("reviewed"):
            continue
        validated.append(case)
    return validated


def build_endpoint_payload(
    *,
    endpoint: str,
    case: dict[str, Any],
    answerer_model: str,
    selector_model: str,
    max_pages: int,
    rag_limit: int,
    rag_strategy: str,
    use_graph_expansion: bool,
) -> dict[str, Any]:
    common = {
        "question": case.get("request_question") or case["question"],
        "answerer_model": answerer_model,
        "include_page_content": True,
    }
    if endpoint == "ask":
        return {
            **common,
            "selector_model": selector_model,
            "max_pages": max_pages,
            "use_graph_expansion": use_graph_expansion,
        }
    if endpoint == "ask-rag":
        return {
            **common,
            "retrieval_mode": "wiki",
            "retrieval_strategy": rag_strategy,
            "limit": rag_limit,
        }
    raise ValueError(f"unsupported endpoint: {endpoint}")


def post_json(
    url: str, payload: dict[str, Any], timeout: float
) -> tuple[int, dict[str, Any]]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed
    except (TimeoutError, socket.timeout) as exc:
        return 598, {"detail": f"request timed out after {timeout:.1f}s: {exc}"}
    except error.URLError as exc:
        return 599, {"detail": str(exc)}


def response_contexts(response: dict[str, Any]) -> list[str]:
    contexts: list[str] = []
    for page in response.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_name = page.get("page_name") or "unknown"
        content = page.get("content") or page.get("summary")
        if isinstance(content, str) and content.strip():
            contexts.append(f"Page: {page_name}\n{content.strip()}")
    return contexts


def deterministic_scores(
    case: dict[str, Any], response: dict[str, Any]
) -> dict[str, Any]:
    page_names = [
        page for page in response.get("pages_used", []) if isinstance(page, str)
    ]
    returned = set(page_names)
    reference = set(case.get("reference_pages", []))
    acceptable = set(case.get("acceptable_pages", []))
    prohibited_patterns = case.get("must_not_pages", [])
    answer = str(response.get("answer") or "")
    folded_answer = answer.casefold()
    required_terms = case.get("required_answer_terms", [])
    forbidden_terms = case.get("forbidden_answer_terms", [])

    scores: dict[str, Any] = {
        "page_count": len(page_names),
        "prohibited_page_hits": sorted(
            page_name
            for page_name in returned
            if any(
                fnmatch.fnmatchcase(page_name, pattern)
                for pattern in prohibited_patterns
            )
        ),
        "required_answer_terms_missing": [
            term for term in required_terms if term.casefold() not in folded_answer
        ],
        "forbidden_answer_terms_present": [
            term for term in forbidden_terms if term.casefold() in folded_answer
        ],
    }
    if required_terms or forbidden_terms:
        scores["deterministic_answer_pass"] = (
            not scores["required_answer_terms_missing"]
            and not scores["forbidden_answer_terms_present"]
        )
    if prohibited_patterns:
        scores["prohibited_page_pass"] = not scores["prohibited_page_hits"]
    if reference:
        hits = returned & reference
        relevant_hits = returned & (reference | acceptable)
        scores["reference_page_precision"] = (
            len(relevant_hits) / len(returned) if returned else 0.0
        )
        scores["reference_page_recall"] = len(hits) / len(reference)
        scores["missing_reference_pages"] = sorted(reference - returned)
    return scores


def create_judge_llm(model: str, provider: str) -> Any:
    os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
    from ragas.llms import llm_factory

    normalized_provider = provider
    normalized_model = model
    if provider == "auto":
        if model.startswith("claude"):
            normalized_provider = "anthropic"
        elif model.startswith(("lmstudio:", "lm-studio:")):
            normalized_provider = "lmstudio"
        elif model.startswith("gpt"):
            normalized_provider = "openai"
        else:
            raise ValueError(
                "cannot infer judge provider; pass --judge-provider "
                "anthropic, openai, or lmstudio"
            )

    if normalized_provider == "anthropic":
        from anthropic import AsyncAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for an Anthropic judge")
        client = AsyncAnthropic(api_key=api_key)
        judge = llm_factory(
            normalized_model,
            provider="anthropic",
            client=client,
        )
        # Ragas 0.4.3 defaults both values, but Anthropic accepts only one.
        judge.model_args.pop("top_p", None)
        # Faithfulness decomposes long answers into claims before judging them.
        # Ragas' 1,024-token default can truncate that structured response.
        judge.model_args["max_tokens"] = 4096
        return judge

    if normalized_provider in {"openai", "lmstudio"}:
        from openai import AsyncOpenAI

        if normalized_provider == "lmstudio":
            normalized_model = normalized_model.split(":", 1)[-1]
            base_url = (
                os.getenv("WIKI_LMSTUDIO_BASE_URL")
                or os.getenv("LMSTUDIO_BASE_URL")
                or "http://127.0.0.1:1234/v1"
            )
            api_key = (
                os.getenv("WIKI_LMSTUDIO_API_KEY")
                or os.getenv("LMSTUDIO_API_KEY")
                or "lm-studio"
            )
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for an OpenAI judge")
            client = AsyncOpenAI(api_key=api_key)
        judge = llm_factory(
            normalized_model,
            provider="openai",
            client=client,
        )
        judge.model_args["max_tokens"] = 4096
        return judge

    raise ValueError(f"unsupported judge provider: {normalized_provider}")


async def score_with_ragas(
    *,
    case: dict[str, Any],
    response: dict[str, Any],
    metric_names: list[str],
    judge_llm: Any,
) -> dict[str, Any]:
    from ragas.metrics.collections import (
        AnswerAccuracy,
        ContextPrecision,
        ContextRecall,
        FactualCorrectness,
        Faithfulness,
        InstanceSpecificRubrics,
    )

    question = case["question"]
    answer = str(response.get("answer") or "")
    contexts = response_contexts(response)
    reference = case.get("reference_answer")
    rubric = case.get("rubric")
    results: dict[str, Any] = {}

    for metric_name in metric_names:
        try:
            if metric_name == "faithfulness":
                if not contexts:
                    results[metric_name] = {"skipped": "no returned page content"}
                    continue
                metric_result = await Faithfulness(llm=judge_llm).ascore(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                )
            elif metric_name == "answer_accuracy":
                if not reference:
                    results[metric_name] = {"skipped": "no reference_answer"}
                    continue
                metric_result = await AnswerAccuracy(llm=judge_llm).ascore(
                    user_input=question,
                    response=answer,
                    reference=reference,
                )
            elif metric_name == "factual_correctness":
                if not reference:
                    results[metric_name] = {"skipped": "no reference_answer"}
                    continue
                metric_result = await FactualCorrectness(llm=judge_llm).ascore(
                    response=answer,
                    reference=reference,
                )
            elif metric_name == "context_precision":
                if not reference:
                    results[metric_name] = {"skipped": "no reference_answer"}
                    continue
                metric_result = await ContextPrecision(llm=judge_llm).ascore(
                    user_input=question,
                    reference=reference,
                    retrieved_contexts=contexts,
                )
            elif metric_name == "context_recall":
                if not reference:
                    results[metric_name] = {"skipped": "no reference_answer"}
                    continue
                metric_result = await ContextRecall(llm=judge_llm).ascore(
                    user_input=question,
                    retrieved_contexts=contexts,
                    reference=reference,
                )
            elif metric_name == "rubric":
                if not rubric:
                    results[metric_name] = {"skipped": "no rubric"}
                    continue
                metric_result = await InstanceSpecificRubrics(llm=judge_llm).ascore(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                    reference=reference,
                    rubrics=rubric,
                )
            else:
                results[metric_name] = {"error": "unsupported metric"}
                continue
            results[metric_name] = {
                "score": float(metric_result.value),
                "reason": metric_result.reason,
            }
        except Exception as exc:  # Keep one failed judge call from losing the run.
            results[metric_name] = {
                "error": f"{type(exc).__name__}: {exc}",
            }
    return results


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["endpoint"], row["answerer_model"]), []).append(row)

    summaries: list[dict[str, Any]] = []
    for (endpoint, model), group in sorted(groups.items()):
        successful = [row for row in group if row["status_code"] == 200]
        summary: dict[str, Any] = {
            "endpoint": endpoint,
            "answerer_model": model,
            "case_count": len(group),
            "success_count": len(successful),
            "success_rate": len(successful) / len(group) if group else 0.0,
        }
        elapsed = [row["elapsed_ms"] for row in successful]
        if elapsed:
            summary["mean_elapsed_ms"] = statistics.fmean(elapsed)
            summary["median_elapsed_ms"] = statistics.median(elapsed)
        for key in (
            "reference_page_precision",
            "reference_page_recall",
            "deterministic_answer_pass",
            "prohibited_page_pass",
        ):
            values = [
                float(row["deterministic"][key])
                for row in successful
                if key in row["deterministic"]
            ]
            if values:
                summary[f"mean_{key}"] = statistics.fmean(values)
        metric_names = {
            name for row in successful for name in row.get("ragas", {})
        }
        for metric_name in sorted(metric_names):
            values = [
                float(row["ragas"][metric_name]["score"])
                for row in successful
                if isinstance(row.get("ragas", {}).get(metric_name), dict)
                and isinstance(row["ragas"][metric_name].get("score"), (int, float))
            ]
            if values:
                summary[f"mean_ragas_{metric_name}"] = statistics.fmean(values)
                summary[f"ragas_{metric_name}_count"] = len(values)
        summaries.append(summary)
    return summaries


def estimated_budget(
    case_count: int,
    endpoint_count: int,
    model_count: int,
    metric_count: int,
    repeats: int = 1,
) -> dict[str, int]:
    endpoint_calls = case_count * endpoint_count * model_count * repeats
    return {
        "cases": case_count,
        "endpoint_variants": endpoint_count,
        "answerer_models": model_count,
        "repeats": repeats,
        "estimated_endpoint_calls": endpoint_calls,
        "estimated_ragas_metric_invocations": endpoint_calls * metric_count,
    }


def _print_summary(summaries: list[dict[str, Any]]) -> None:
    print("\nSUMMARY")
    for summary in summaries:
        metrics = " ".join(
            f"{key}={value:.3f}"
            for key, value in summary.items()
            if key.startswith("mean_") and isinstance(value, (int, float))
        )
        print(
            f"{summary['endpoint']} / {summary['answerer_model']}: "
            f"{summary['success_count']}/{summary['case_count']} successful {metrics}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8010",
        help="Wiki API base URL.",
    )
    parser.add_argument(
        "--endpoints",
        default=",".join(DEFAULT_ENDPOINTS),
        help="Comma-separated endpoint names: ask,ask-rag.",
    )
    parser.add_argument(
        "--answerer-models",
        required=True,
        help="Comma-separated answerer model overrides.",
    )
    parser.add_argument("--selector-model", default="claude-sonnet-5")
    parser.add_argument("--max-pages", type=int, default=7)
    parser.add_argument("--rag-limit", type=int, default=7)
    parser.add_argument(
        "--rag-strategy",
        choices=["legacy_topk", "diverse_pages"],
        default="diverse_pages",
    )
    graph_expansion_group = parser.add_mutually_exclusive_group()
    graph_expansion_group.add_argument(
        "--graph-expansion",
        dest="use_graph_expansion",
        action="store_true",
        help="Use remaining max-pages slots for ranked related-page summaries.",
    )
    graph_expansion_group.add_argument(
        "--no-graph-expansion",
        dest="use_graph_expansion",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.set_defaults(use_graph_expansion=False)
    parser.add_argument("--only-reviewed", action="store_true")
    parser.add_argument(
        "--case-ids",
        default="",
        help="Optional comma-separated case IDs for a small smoke or rerun.",
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--metrics",
        default=",".join(DEFAULT_METRICS),
        help=(
            "Ragas metrics: answer_accuracy, faithfulness, factual_correctness, "
            "context_precision, context_recall, rubric. Empty disables Ragas."
        ),
    )
    parser.add_argument("--judge-model", default="claude-sonnet-4-6")
    parser.add_argument(
        "--judge-provider",
        choices=["auto", "anthropic", "openai", "lmstudio"],
        default="auto",
    )
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--max-estimated-endpoint-calls", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    case_path = args.cases if args.cases.is_absolute() else REPO_ROOT / args.cases
    try:
        cases = load_cases(case_path, only_reviewed=args.only_reviewed)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not cases:
        parser.error("the selected dataset contains no runnable cases")
    requested_case_ids = split_csv(args.case_ids)
    if requested_case_ids:
        by_id = {case["id"]: case for case in cases}
        missing_case_ids = [case_id for case_id in requested_case_ids if case_id not in by_id]
        if missing_case_ids:
            parser.error(f"unknown or filtered case IDs: {missing_case_ids}")
        cases = [by_id[case_id] for case_id in requested_case_ids]

    endpoints = split_csv(args.endpoints)
    invalid_endpoints = sorted(set(endpoints) - set(DEFAULT_ENDPOINTS))
    if invalid_endpoints or not endpoints:
        parser.error(f"unsupported endpoints: {invalid_endpoints or endpoints}")
    models = split_csv(args.answerer_models)
    if not models:
        parser.error("--answerer-models must contain at least one model")
    metrics = split_csv(args.metrics)
    invalid_metrics = sorted(set(metrics) - SUPPORTED_METRICS)
    if invalid_metrics:
        parser.error(f"unsupported metrics: {invalid_metrics}")
    if not 1 <= args.max_pages <= 10:
        parser.error("--max-pages must be between 1 and 10")
    if not 1 <= args.rag_limit <= 20:
        parser.error("--rag-limit must be between 1 and 20")
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    budget = estimated_budget(
        len(cases), len(endpoints), len(models), len(metrics), args.repeats
    )
    if budget["estimated_endpoint_calls"] > args.max_estimated_endpoint_calls:
        parser.error(
            f"estimated {budget['estimated_endpoint_calls']} endpoint calls exceeds "
            f"--max-estimated-endpoint-calls {args.max_estimated_endpoint_calls}"
        )
    print("EVAL BUDGET:", json.dumps(budget, indent=2))
    if args.dry_run:
        return 0

    judge_llm = None
    judge_loop = None
    if metrics:
        try:
            judge_llm = create_judge_llm(args.judge_model, args.judge_provider)
            judge_loop = asyncio.new_event_loop()
        except (ImportError, ValueError) as exc:
            parser.error(f"cannot initialize Ragas judge: {exc}")

    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            for answerer_model in models:
                for endpoint in endpoints:
                    payload = build_endpoint_payload(
                        endpoint=endpoint,
                        case=case,
                        answerer_model=answerer_model,
                        selector_model=args.selector_model,
                        max_pages=args.max_pages,
                        rag_limit=args.rag_limit,
                        rag_strategy=args.rag_strategy,
                        use_graph_expansion=args.use_graph_expansion,
                    )
                    started = time.perf_counter()
                    status_code, response = post_json(
                        f"{args.base_url.rstrip('/')}/wiki/{endpoint}",
                        payload,
                        args.timeout,
                    )
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    row: dict[str, Any] = {
                        "repeat": repeat,
                        "case_id": case["id"],
                        "reviewed": bool(case.get("reviewed")),
                        "question": case["question"],
                        "endpoint": endpoint,
                        "answerer_model": answerer_model,
                        "selector_model": (
                            args.selector_model if endpoint == "ask" else None
                        ),
                        "request_payload": payload,
                        "status_code": status_code,
                        "elapsed_ms": elapsed_ms,
                        "answer": response.get("answer", ""),
                        "citations": response.get("citations", []),
                        "pages_used": response.get("pages_used", []),
                        "pages": response.get("pages", []),
                        "trace": response.get("trace", {}),
                        "error": response.get("detail") if status_code != 200 else None,
                        "deterministic": {},
                        "ragas": {},
                    }
                    if status_code == 200:
                        row["deterministic"] = deterministic_scores(case, response)
                        if (
                            metrics
                            and judge_llm is not None
                            and judge_loop is not None
                        ):
                            row["ragas"] = judge_loop.run_until_complete(
                                score_with_ragas(
                                    case=case,
                                    response=response,
                                    metric_names=metrics,
                                    judge_llm=judge_llm,
                                )
                            )
                    rows.append(row)
                    print(
                        f"repeat={repeat} {case['id']} {endpoint} {answerer_model}: "
                        f"status={status_code} elapsed_ms={elapsed_ms}",
                        flush=True,
                    )

    if judge_loop is not None:
        judge_loop.close()
    summaries = summarize(rows)
    result = {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dataset": str(case_path),
        "configuration": {
            "base_url": args.base_url,
            "endpoints": endpoints,
            "answerer_models": models,
            "selector_model": args.selector_model,
            "max_pages": args.max_pages,
            "rag_limit": args.rag_limit,
            "rag_strategy": args.rag_strategy,
            "use_graph_expansion": args.use_graph_expansion,
            "repeats": args.repeats,
            "ragas_metrics": metrics,
            "judge_model": args.judge_model if metrics else None,
            "judge_provider": args.judge_provider if metrics else None,
        },
        "budget": budget,
        "summary": summaries,
        "rows": rows,
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
    _print_summary(summaries)
    print(f"\nwrote {output_path}")
    return 0 if all(row["status_code"] == 200 for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
