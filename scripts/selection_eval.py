"""Run the page-selection gold set against context-pack or ask selection and score it.

Two endpoint modes, selected with --endpoint:
- "context-pack" (default): mirrors the original selection eval. Requires the
  response trace to carry `skeleton_enforcement` and reports backfill metrics.
- "ask": POSTs /wiki/ask/select-pages instead. This uses the ask catalog scope
  without paying for an answerer or graph expansion. The ask selector has no
  skeleton enforcement or backfill pass, so those metrics are skipped.

Both modes reuse the same shared plumbing (run_pass, median_summary,
miss_frequency, score_case) -- only the HTTP call and the trace-dependent
metrics differ.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
import sys
import urllib.request
from fnmatch import fnmatch

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.selection_scoring import aggregate, score_case, miss_frequency  # noqa: E402

CONTEXT_PACK_ONLY_METRICS = [
    "mean_pack_chars",
    "backfill_case_rate",
    "mean_backfills_per_case",
]
MEDIAN_METRICS = [
    "mean_must_have_recall",
    "mean_precision",
    "leak_free_rate",
    "mean_selector_tokens",
    "mean_selector_wall_time_ms",
    *CONTEXT_PACK_ONLY_METRICS,
]

DEFAULT_MAX_REPEATS = 3
DEFAULT_MAX_ESTIMATED_CALLS = 200


def call_context_pack(base_url: str, request_payload: dict) -> dict:
    body = dict(request_payload)
    body.setdefault("include_page_content", True)
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/wiki/context-pack",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def call_ask(base_url: str, request_payload: dict) -> dict:
    body = dict(request_payload)
    body.setdefault("include_page_content", False)
    # The selector-only endpoint does not accept or execute answerer/expansion
    # controls. Strip legacy gold fields so the request records its real scope.
    for field_name in (
        "answerer_model",
        "answerer_reasoning_effort",
        "use_graph_expansion",
    ):
        body.pop(field_name, None)
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/wiki/ask/select-pages",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


ENDPOINT_CALLERS = {
    "context-pack": call_context_pack,
    "ask": call_ask,
}


def check_gold_invariants(gold: dict) -> None:
    """Verify no non-glob must_have/acceptable page matches any must_not pattern.

    A hand-edit to the gold set could otherwise mark a page as simultaneously
    recalled (must_have/acceptable) and leaked (must_not), which would make
    scoring internally inconsistent.
    """
    for case in gold["cases"]:
        labels = case["labels"]
        must_not = labels.get("must_not", [])
        for bucket in ("must_have", "acceptable"):
            for page in labels.get(bucket, []):
                for pattern in must_not:
                    if fnmatch(page, pattern):
                        raise RuntimeError(
                            f"{case['id']}: {bucket} page {page!r} matches "
                            f"must_not pattern {pattern!r}"
                        )


def _build_context_pack_row(case: dict, response: dict, pages_used: list) -> dict:
    pack_chars = sum(len(page.get("content") or "") for page in response.get("pages", []))
    trace = response.get("trace") or {}
    if "skeleton_enforcement" not in trace:
        raise RuntimeError(
            f"{case['id']}: response trace lacks skeleton_enforcement — "
            "is the server running pre-enforcement code?"
        )
    enforcement = trace.get("skeleton_enforcement") or {}
    timing_summary = trace.get("timing_summary") or {}
    selector_wall_time_ms = timing_summary.get("request_wall_time_ms")
    if not isinstance(selector_wall_time_ms, (int, float)):
        raise RuntimeError(
            f"{case['id']}: response trace lacks timing_summary.request_wall_time_ms"
        )
    return {
        "pack_chars": pack_chars,
        "selector_tokens": trace.get("token_summary"),
        "selector_wall_time_ms": selector_wall_time_ms,
        "backfilled": enforcement.get("backfilled", []),
        "dropped": enforcement.get("dropped", []),
        "trimmed": enforcement.get("trimmed", []),
    }


def _build_ask_row(case: dict, response: dict, pages_used: list) -> dict:
    # Ask selection has no skeleton_enforcement/backfill pass — the row carries
    # none of the context-pack-only fields. Selector usage is still recorded.
    trace = response.get("trace") or {}
    retrieval = trace.get("retrieval") or {}
    token_summary = retrieval.get("token_summary")
    if not isinstance(token_summary, dict):
        raise RuntimeError(
            f"{case['id']}: response trace lacks retrieval token_summary"
        )
    total = trace.get("total") or {}
    selector_wall_time_ms = total.get("request_wall_time_ms")
    if not isinstance(selector_wall_time_ms, (int, float)):
        raise RuntimeError(
            f"{case['id']}: response trace lacks total request_wall_time_ms"
        )
    return {
        "selector_tokens": token_summary,
        "selector_wall_time_ms": selector_wall_time_ms,
    }


ROW_BUILDERS = {
    "context-pack": _build_context_pack_row,
    "ask": _build_ask_row,
}


def run_pass(
    cases: list[dict],
    base_url: str,
    pass_number: int,
    max_pages_override: int | None = None,
    endpoint: str = "context-pack",
    selector_model_override: str | None = None,
) -> tuple[list[dict], dict]:
    caller = ENDPOINT_CALLERS[endpoint]
    build_row_extra = ROW_BUILDERS[endpoint]
    response_key = (
        "malformed /wiki/context-pack response"
        if endpoint == "context-pack"
        else "malformed /wiki/ask/select-pages response"
    )

    rows = []
    for case in cases:
        request = dict(case["request"])
        if max_pages_override is not None:
            request["max_pages"] = max_pages_override
        if selector_model_override is not None:
            request["selector_model"] = selector_model_override
        response = caller(base_url, request)
        pages_used = response.get("pages_used")
        if not isinstance(pages_used, list):
            raise RuntimeError(f"{case['id']}: {response_key}: missing pages_used")
        score = score_case(case["labels"], pages_used)
        row = {
            "id": case["id"],
            "reviewed": bool(case.get("reviewed")),
            "pages_used": pages_used,
            "max_pages_sent": request.get("max_pages"),
            "selector_model_sent": request.get("selector_model"),
            **build_row_extra(case, response, pages_used),
            **score,
        }
        rows.append(row)
        backfilled_note = ""
        if "backfilled" in row:
            backfilled_note = f" backfilled={[item['page'] for item in row['backfilled']]}"
        print(
            f"[pass {pass_number}] {case['id']}: recall={score['must_have_recall']:.2f} "
            f"leaks={score['leaks']} missing={score['missing']}{backfilled_note}"
        )

    summary = aggregate(rows)
    if endpoint == "context-pack":
        summary["mean_pack_chars"] = (
            sum(row["pack_chars"] for row in rows) / len(rows) if rows else 0
        )
        summary["backfill_case_rate"] = (
            len([row for row in rows if row["backfilled"]]) / len(rows) if rows else 0
        )
        summary["mean_backfills_per_case"] = (
            sum(len(row["backfilled"]) for row in rows) / len(rows) if rows else 0
        )
    token_totals = [
        (row["selector_tokens"] or {}).get("total_tracked_tokens")
        for row in rows
        if isinstance(row.get("selector_tokens"), dict)
    ]
    token_totals = [t for t in token_totals if isinstance(t, (int, float))]
    summary["mean_selector_tokens"] = (
        sum(token_totals) / len(token_totals) if token_totals else 0
    )
    selector_wall_times = [
        row["selector_wall_time_ms"]
        for row in rows
        if isinstance(row.get("selector_wall_time_ms"), (int, float))
    ]
    if selector_wall_times:
        summary["mean_selector_wall_time_ms"] = (
            sum(selector_wall_times) / len(selector_wall_times)
        )
    return rows, summary


def median_summary(passes: list[dict]) -> dict:
    out = {}
    for metric in MEDIAN_METRICS:
        if not all(metric in p["summary"] for p in passes):
            # Endpoint modes (e.g. "ask") that skip context-pack-only metrics
            # simply omit them here rather than erroring.
            continue
        values = [p["summary"][metric] for p in passes]
        out[metric] = {
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    out["passes"] = len(passes)
    return out


def effective_max_pages(cases: list[dict], max_pages_override: int | None) -> dict:
    """The max_pages actually sent per case, for results-payload provenance.

    Replaces reliance on the CLI --max-pages override key alone: that key is
    None whenever no override is passed, which silently hides the per-case
    request max_pages actually used. This records the min/max actually sent
    across all cases in the run, whether from an override or from each case's
    own request payload.
    """
    sent = [
        max_pages_override if max_pages_override is not None else case["request"].get("max_pages")
        for case in cases
    ]
    sent = [value for value in sent if isinstance(value, int)]
    if not sent:
        return {"min": None, "max": None}
    return {"min": min(sent), "max": max(sent)}


def validate_eval_budget(
    *,
    case_count: int,
    repeats: int,
    max_estimated_calls: int = DEFAULT_MAX_ESTIMATED_CALLS,
    allow_high_repeats: bool = False,
) -> int:
    """Validate and return the selector-call budget before any network request."""
    if repeats < 1:
        raise ValueError("--repeats must be at least 1")
    if repeats > DEFAULT_MAX_REPEATS and not allow_high_repeats:
        raise ValueError(
            f"--repeats above {DEFAULT_MAX_REPEATS} requires --allow-high-repeats"
        )
    if max_estimated_calls < 1:
        raise ValueError("--max-estimated-calls must be at least 1")
    estimated_calls = case_count * repeats
    if estimated_calls > max_estimated_calls:
        raise ValueError(
            f"estimated {estimated_calls} LLM calls exceeds --max-estimated-calls "
            f"{max_estimated_calls}; narrow the case set or explicitly raise the cap"
        )
    return estimated_calls


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument(
        "--endpoint", choices=["context-pack", "ask"], default="context-pack",
        help="Which endpoint to evaluate against (default: context-pack, backward compatible).",
    )
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--label", required=True, help="Report label, e.g. 'baseline'.")
    parser.add_argument("--only-reviewed", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--allow-high-repeats",
        action="store_true",
        help=f"Acknowledge runs above {DEFAULT_MAX_REPEATS} repeats.",
    )
    parser.add_argument(
        "--max-estimated-calls",
        type=int,
        default=DEFAULT_MAX_ESTIMATED_CALLS,
        help=(
            "Abort before network calls when cases × repeats exceeds this cap "
            f"(default: {DEFAULT_MAX_ESTIMATED_CALLS})."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the call budget without making requests or writing a report.",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Override every case request's max_pages (budget sensitivity probes).",
    )
    parser.add_argument(
        "--selector-model",
        default=None,
        help="Override the selector model for every case in the run.",
    )
    args = parser.parse_args()

    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    check_gold_invariants(gold)
    cases = [
        case for case in gold["cases"]
        if case.get("reviewed") or not args.only_reviewed
    ]
    try:
        estimated_calls = validate_eval_budget(
            case_count=len(cases),
            repeats=args.repeats,
            max_estimated_calls=args.max_estimated_calls,
            allow_high_repeats=args.allow_high_repeats,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(
        "EVAL BUDGET:",
        json.dumps(
            {
                "endpoint": args.endpoint,
                "cases": len(cases),
                "repeats": args.repeats,
                "estimated_llm_calls": estimated_calls,
                "selector_model": args.selector_model,
            },
            indent=2,
        ),
    )
    if args.dry_run:
        return

    passes = []
    for pass_number in range(1, args.repeats + 1):
        rows, summary = run_pass(
            cases,
            args.base_url,
            pass_number,
            args.max_pages,
            endpoint=args.endpoint,
            selector_model_override=args.selector_model,
        )
        passes.append({"summary": summary, "cases": rows})
        print(f"\n[pass {pass_number}] SUMMARY:", json.dumps(summary, indent=2))

    medians = median_summary(passes)
    print("\nMEDIAN SUMMARY:", json.dumps(medians, indent=2))

    freq = miss_frequency([p["cases"] for p in passes])
    print("\nMISS FREQUENCY (systematic = missed in >= ceil(2/3*repeats) passes):")
    for entry in freq["systematic"]:
        print(f"  SYSTEMATIC {entry['case_id']}: {entry['page']} missed {entry['missed']}/{entry['repeats']}")
    for entry in freq["stochastic"]:
        print(f"  stochastic {entry['case_id']}: {entry['page']} missed {entry['missed']}/{entry['repeats']}")

    max_pages_summary = effective_max_pages(cases, args.max_pages)

    report_root = "ask-evals" if args.endpoint == "ask" else "selection-evals"
    out_dir = (
        REPO_ROOT / "reports" / report_root
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps(
            {
                "endpoint": args.endpoint,
                "repeats": args.repeats,
                "estimated_llm_calls": estimated_calls,
                "max_pages_override": args.max_pages,
                "selector_model_override": args.selector_model,
                "effective_max_pages": max_pages_summary,
                "passes": passes,
                "median_summary": medians,
                "miss_frequency": freq,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("wrote", out_dir / "results.json")


if __name__ == "__main__":
    main()
