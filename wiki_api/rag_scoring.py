"""Deterministic scoring helpers for wiki-RAG retrieval and grounding."""
from __future__ import annotations

import math
import re
from fnmatch import fnmatch
from typing import Any

CONTROL_PAGES = {"index.md", "RUNTIME_RULES.md"}
FOODEX_IDENTIFIER_RE = re.compile(r"\b(?:F\d{2}|A[0-9A-Z]{4})\b")


def _matches_any(value: str, patterns: list[str]) -> bool:
    return any(fnmatch(value, pattern) for pattern in patterns)


def score_retrieval_case(
    *,
    labels: dict[str, Any],
    raw_page_names: list[str],
    final_page_names: list[str],
    requested_page_limit: int | None = None,
) -> dict[str, Any]:
    """Score one retrieval result without conflating chunks and unique pages."""
    raw_pages = [page for page in raw_page_names if page not in CONTROL_PAGES]
    final_page_slots = [
        page for page in final_page_names if page not in CONTROL_PAGES
    ]
    final_pages = list(dict.fromkeys(final_page_slots))
    unique_raw_pages = list(dict.fromkeys(raw_pages))
    must_have = list(
        labels.get("must_have_pages", labels.get("must_have", []))
    )
    acceptable = list(
        labels.get("acceptable_pages", labels.get("acceptable", []))
    )
    must_not = list(
        labels.get("must_not_pages", labels.get("must_not", []))
    )
    allowed = set(must_have) | set(acceptable)

    missing = [page for page in must_have if page not in final_pages]
    leaks = [page for page in final_pages if _matches_any(page, must_not)]
    unlabeled = [
        page for page in final_pages if page not in allowed and page not in leaks
    ]
    recall = (
        1.0
        if not must_have
        else (len(must_have) - len(missing)) / len(must_have)
    )
    precision = (
        1.0
        if not final_pages
        else len([page for page in final_pages if page in allowed]) / len(final_pages)
    )
    candidate_duplicate_count = len(raw_pages) - len(unique_raw_pages)
    candidate_duplicate_ratio = (
        candidate_duplicate_count / len(raw_pages) if raw_pages else 0.0
    )
    topk_limit = requested_page_limit or len(final_page_slots)
    preassembly_slots = raw_pages[:topk_limit]
    preassembly_duplicate_count = len(preassembly_slots) - len(
        set(preassembly_slots)
    )
    preassembly_duplicate_slot_waste = (
        preassembly_duplicate_count / len(preassembly_slots)
        if preassembly_slots
        else 0.0
    )
    final_duplicate_count = len(final_page_slots) - len(final_pages)
    duplicate_slot_waste = (
        final_duplicate_count / len(final_page_slots)
        if final_page_slots
        else 0.0
    )

    role_pages = labels.get("role_pages", {})
    required_roles = list(labels.get("required_roles", []))
    covered_roles = [
        role
        for role in required_roles
        if any(page in final_pages for page in role_pages.get(role, []))
    ]
    missing_roles = [role for role in required_roles if role not in covered_roles]
    role_coverage = (
        1.0
        if not required_roles
        else len(covered_roles) / len(required_roles)
    )

    return {
        "must_have_recall": recall,
        "precision": precision,
        "missing": missing,
        "leaks": leaks,
        "unlabeled": unlabeled,
        "raw_chunk_count": len(raw_pages),
        "raw_unique_page_count": len(unique_raw_pages),
        "final_unique_page_count": len(final_pages),
        "candidate_duplicate_chunk_count": candidate_duplicate_count,
        "candidate_duplicate_ratio": candidate_duplicate_ratio,
        "preassembly_duplicate_slot_waste": preassembly_duplicate_slot_waste,
        "final_duplicate_page_count": final_duplicate_count,
        "duplicate_slot_waste": duplicate_slot_waste,
        "covered_roles": covered_roles,
        "missing_roles": missing_roles,
        "role_coverage": role_coverage,
    }


def validate_citations(
    citations: list[str], allowed_pages: list[str]
) -> dict[str, list[str]]:
    """Separate citations that name supplied evidence from invalid citations."""
    allowed = set(allowed_pages)
    valid = list(dict.fromkeys(citation for citation in citations if citation in allowed))
    invalid = list(
        dict.fromkeys(citation for citation in citations if citation not in allowed)
    )
    return {"valid": valid, "invalid": invalid}


def unsupported_identifiers(
    *,
    text: str,
    citations: list[str],
    evidence_by_page: dict[str, str],
) -> list[str]:
    """Return FoodEx2-like identifiers absent from all cited evidence."""
    identifiers = list(dict.fromkeys(FOODEX_IDENTIFIER_RE.findall(text.upper())))
    cited_evidence = "\n".join(
        evidence_by_page[citation]
        for citation in citations
        if citation in evidence_by_page
    ).upper()
    return [
        identifier for identifier in identifiers if identifier not in cited_evidence
    ]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def aggregate_retrieval_scores(
    rows: list[dict[str, Any]],
) -> dict[str, float | int]:
    """Aggregate retrieval quality, diversity, and latency metrics."""
    if not rows:
        return {
            "case_count": 0,
            "mean_must_have_recall": 0.0,
            "mean_precision": 0.0,
            "leak_free_rate": 0.0,
            "mean_unique_pages": 0.0,
            "mean_candidate_duplicate_ratio": 0.0,
            "mean_preassembly_duplicate_slot_waste": 0.0,
            "mean_duplicate_slot_waste": 0.0,
            "mean_role_coverage": 0.0,
            "mean_retrieval_ms": 0.0,
            "p95_retrieval_ms": 0.0,
        }
    count = len(rows)
    latencies = [
        float(row["retrieval_ms"])
        for row in rows
        if isinstance(row.get("retrieval_ms"), (int, float))
    ]
    return {
        "case_count": count,
        "mean_must_have_recall": sum(
            row["must_have_recall"] for row in rows
        )
        / count,
        "mean_precision": sum(row["precision"] for row in rows) / count,
        "leak_free_rate": len([row for row in rows if not row["leaks"]])
        / count,
        "mean_unique_pages": sum(
            row["final_unique_page_count"] for row in rows
        )
        / count,
        "mean_candidate_duplicate_ratio": sum(
            row["candidate_duplicate_ratio"] for row in rows
        )
        / count,
        "mean_preassembly_duplicate_slot_waste": sum(
            row["preassembly_duplicate_slot_waste"] for row in rows
        )
        / count,
        "mean_duplicate_slot_waste": sum(
            row["duplicate_slot_waste"] for row in rows
        )
        / count,
        "mean_role_coverage": sum(row["role_coverage"] for row in rows)
        / count,
        "mean_retrieval_ms": (
            sum(latencies) / len(latencies) if latencies else 0.0
        ),
        "p95_retrieval_ms": _percentile(latencies, 0.95),
    }
