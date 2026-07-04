"""Deterministic scoring for page-selection gold cases.

Excluded from scoring: pages present by construction in every context pack.
"""
from __future__ import annotations

from fnmatch import fnmatch

ALWAYS_PRESENT = {"index.md", "RUNTIME_RULES.md"}


def _matches_any(page: str, patterns: list[str]) -> bool:
    return any(fnmatch(page, pattern) for pattern in patterns)


def score_case(labels: dict, pages_used: list[str]) -> dict:
    selected = [page for page in pages_used if page not in ALWAYS_PRESENT]
    must_have = list(labels.get("must_have", []))
    acceptable = list(labels.get("acceptable", []))
    must_not = list(labels.get("must_not", []))
    allowed = set(must_have) | set(acceptable)

    missing = [page for page in must_have if page not in selected]
    leaks = [page for page in selected if _matches_any(page, must_not)]
    unlabeled = [
        page for page in selected if page not in allowed and page not in leaks
    ]
    recall = 1.0 if not must_have else (len(must_have) - len(missing)) / len(must_have)
    precision = 1.0 if not selected else len(
        [page for page in selected if page in allowed]
    ) / len(selected)
    return {
        "must_have_recall": recall,
        "precision": precision,
        "missing": missing,
        "leaks": leaks,
        "unlabeled": unlabeled,
    }


def aggregate(case_scores: list[dict]) -> dict:
    count = len(case_scores)
    if count == 0:
        return {
            "mean_must_have_recall": 0.0,
            "mean_precision": 0.0,
            "leak_free_rate": 0.0,
            "case_count": 0,
        }
    return {
        "mean_must_have_recall": sum(s["must_have_recall"] for s in case_scores) / count,
        "mean_precision": sum(s["precision"] for s in case_scores) / count,
        "leak_free_rate": len([s for s in case_scores if not s["leaks"]]) / count,
        "case_count": count,
    }
