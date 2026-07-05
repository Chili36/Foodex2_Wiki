"""Run the page-selection gold set against /wiki/context-pack and score it."""
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

from wiki_api.selection_scoring import aggregate, score_case  # noqa: E402

MEDIAN_METRICS = [
    "mean_must_have_recall",
    "mean_precision",
    "leak_free_rate",
    "mean_pack_chars",
    "backfill_case_rate",
    "mean_backfills_per_case",
    "mean_selector_tokens",
]


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


def run_pass(cases: list[dict], base_url: str, pass_number: int) -> tuple[list[dict], dict]:
    rows = []
    for case in cases:
        response = call_context_pack(base_url, case["request"])
        pages_used = response.get("pages_used")
        if not isinstance(pages_used, list):
            raise RuntimeError(
                f"{case['id']}: malformed /wiki/context-pack response: missing pages_used"
            )
        pack_chars = sum(len(page.get("content") or "") for page in response.get("pages", []))
        score = score_case(case["labels"], pages_used)
        trace = response.get("trace") or {}
        if "skeleton_enforcement" not in trace:
            raise RuntimeError(
                f"{case['id']}: response trace lacks skeleton_enforcement — "
                "is the server running pre-enforcement code?"
            )
        enforcement = trace.get("skeleton_enforcement") or {}
        row = {
            "id": case["id"],
            "reviewed": bool(case.get("reviewed")),
            "pages_used": pages_used,
            "pack_chars": pack_chars,
            "selector_tokens": (response.get("trace") or {}).get("token_summary"),
            "backfilled": enforcement.get("backfilled", []),
            "dropped": enforcement.get("dropped", []),
            **score,
        }
        rows.append(row)
        print(
            f"[pass {pass_number}] {case['id']}: recall={score['must_have_recall']:.2f} "
            f"leaks={score['leaks']} missing={score['missing']} "
            f"backfilled={[item['page'] for item in row['backfilled']]}"
        )

    summary = aggregate(rows)
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
    return rows, summary


def median_summary(passes: list[dict]) -> dict:
    out = {}
    for metric in MEDIAN_METRICS:
        values = [p["summary"][metric] for p in passes]
        out[metric] = {
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    out["passes"] = len(passes)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--label", required=True, help="Report label, e.g. 'baseline'.")
    parser.add_argument("--only-reviewed", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()

    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    check_gold_invariants(gold)
    cases = [
        case for case in gold["cases"]
        if case.get("reviewed") or not args.only_reviewed
    ]

    passes = []
    for pass_number in range(1, args.repeats + 1):
        rows, summary = run_pass(cases, args.base_url, pass_number)
        passes.append({"summary": summary, "cases": rows})
        print(f"\n[pass {pass_number}] SUMMARY:", json.dumps(summary, indent=2))

    medians = median_summary(passes)
    print("\nMEDIAN SUMMARY:", json.dumps(medians, indent=2))

    out_dir = (
        REPO_ROOT / "reports" / "selection-evals"
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps(
            {"repeats": args.repeats, "passes": passes, "median_summary": medians},
            ensure_ascii=False,
            indent=2,
        )
    )
    print("wrote", out_dir / "results.json")


if __name__ == "__main__":
    main()
