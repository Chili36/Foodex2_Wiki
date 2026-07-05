"""Run the page-selection gold set against /wiki/context-pack and score it."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.request
from fnmatch import fnmatch

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from wiki_api.selection_scoring import aggregate, score_case  # noqa: E402


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--gold-path", default="evals/selection/gold_cases.json")
    parser.add_argument("--label", required=True, help="Report label, e.g. 'baseline'.")
    parser.add_argument("--only-reviewed", action="store_true")
    args = parser.parse_args()

    gold = json.loads(pathlib.Path(args.gold_path).read_text())
    check_gold_invariants(gold)
    cases = [
        case for case in gold["cases"]
        if case.get("reviewed") or not args.only_reviewed
    ]
    rows = []
    for case in cases:
        response = call_context_pack(args.base_url, case["request"])
        pages_used = response.get("pages_used")
        if not isinstance(pages_used, list):
            raise RuntimeError(
                f"{case['id']}: malformed /wiki/context-pack response: missing pages_used"
            )
        pack_chars = sum(len(page.get("content") or "") for page in response.get("pages", []))
        score = score_case(case["labels"], pages_used)
        enforcement = (response.get("trace") or {}).get("skeleton_enforcement") or {}
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
            f"{case['id']}: recall={score['must_have_recall']:.2f} "
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
    out_dir = (
        REPO_ROOT / "reports" / "selection-evals"
        / f"{dt.date.today().isoformat()}-{args.label}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2)
    )
    print("\nSUMMARY:", json.dumps(summary, indent=2))
    print("wrote", out_dir / "results.json")


if __name__ == "__main__":
    main()
