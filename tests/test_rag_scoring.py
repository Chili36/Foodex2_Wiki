from wiki_api.rag_scoring import (
    aggregate_retrieval_scores,
    score_retrieval_case,
    unsupported_identifiers,
    validate_citations,
)


LABELS = {
    "must_have_pages": [
        "base-term-selection.md",
        "pesticides-foodex2.md",
        "term-type-facet-constraints.md",
    ],
    "acceptable_pages": ["facet-coding-rules.md"],
    "must_not_pages": ["contaminants-foodex2.md", "maintenance-*"],
    "required_roles": ["base_term", "validation", "domain_overlay"],
    "role_pages": {
        "base_term": ["base-term-selection.md"],
        "validation": ["term-type-facet-constraints.md"],
        "domain_overlay": ["pesticides-foodex2.md"],
    },
}


def test_score_retrieval_distinguishes_chunks_from_unique_pages() -> None:
    score = score_retrieval_case(
        labels=LABELS,
        raw_page_names=[
            "pesticides-foodex2.md",
            "pesticides-foodex2.md",
            "pesticides-foodex2.md",
            "contaminants-foodex2.md",
        ],
        final_page_names=[
            "pesticides-foodex2.md",
            "contaminants-foodex2.md",
        ],
        requested_page_limit=2,
    )

    assert score["must_have_recall"] == 1 / 3
    assert score["raw_chunk_count"] == 4
    assert score["raw_unique_page_count"] == 2
    assert score["final_unique_page_count"] == 2
    assert score["candidate_duplicate_chunk_count"] == 2
    assert score["candidate_duplicate_ratio"] == 0.5
    assert score["preassembly_duplicate_slot_waste"] == 0.5
    assert score["duplicate_slot_waste"] == 0.0
    assert score["leaks"] == ["contaminants-foodex2.md"]
    assert score["role_coverage"] == 1 / 3


def test_score_retrieval_deduplicates_final_pages() -> None:
    score = score_retrieval_case(
        labels=LABELS,
        raw_page_names=["base-term-selection.md"],
        final_page_names=[
            "base-term-selection.md",
            "base-term-selection.md",
            "term-type-facet-constraints.md",
            "pesticides-foodex2.md",
        ],
    )

    assert score["must_have_recall"] == 1.0
    assert score["precision"] == 1.0
    assert score["final_unique_page_count"] == 3
    assert score["role_coverage"] == 1.0


def test_validate_citations_rejects_pages_outside_evidence() -> None:
    result = validate_citations(
        ["base-term-selection.md", "invented.md", "base-term-selection.md"],
        ["base-term-selection.md"],
    )

    assert result == {
        "valid": ["base-term-selection.md"],
        "invalid": ["invented.md"],
    }


def test_unsupported_identifiers_checks_only_cited_evidence() -> None:
    unsupported = unsupported_identifiers(
        text="Use A0C60 with F01 and F02.A0CEY, not A03ZN.",
        citations=["vmpr-foodex2.md"],
        evidence_by_page={
            "vmpr-foodex2.md": "Use A0C60 with explicit F01 and F02.A0CEY.",
            "packaging-facets.md": "Pizza may use A03ZN.",
        },
    )

    assert unsupported == ["A03ZN"]


def test_aggregate_retrieval_scores_reports_p95() -> None:
    rows = [
        {
            "must_have_recall": 1.0,
            "precision": 1.0,
            "leaks": [],
            "final_unique_page_count": 7,
            "candidate_duplicate_ratio": 0.4,
            "preassembly_duplicate_slot_waste": 0.3,
            "duplicate_slot_waste": 0.1,
            "role_coverage": 1.0,
            "retrieval_ms": 100,
        },
        {
            "must_have_recall": 0.5,
            "precision": 0.75,
            "leaks": ["contaminants-foodex2.md"],
            "final_unique_page_count": 5,
            "candidate_duplicate_ratio": 0.6,
            "preassembly_duplicate_slot_waste": 0.5,
            "duplicate_slot_waste": 0.3,
            "role_coverage": 2 / 3,
            "retrieval_ms": 900,
        },
    ]

    summary = aggregate_retrieval_scores(rows)

    assert summary["case_count"] == 2
    assert summary["mean_must_have_recall"] == 0.75
    assert summary["leak_free_rate"] == 0.5
    assert summary["mean_unique_pages"] == 6
    assert summary["mean_candidate_duplicate_ratio"] == 0.5
    assert summary["mean_preassembly_duplicate_slot_waste"] == 0.4
    assert summary["mean_duplicate_slot_waste"] == 0.2
    assert summary["p95_retrieval_ms"] == 900
