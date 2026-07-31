from __future__ import annotations

from typing import Any

import wiki_api.qdrant_ask as qdrant_ask


def _wiki_result(page_name: str, rank: int, heading: str) -> dict[str, Any]:
    return {
        "score": 1 - rank / 100,
        "payload": {
            "chunk_id": f"{page_name}#{rank}",
            "page_name": page_name,
            "title": page_name.removesuffix(".md"),
            "category": "guidance",
            "source_tier": "local_policy",
            "heading_path": heading,
            "summary": f"Summary for {page_name}",
            "source_path": f"raw/efsa-guidance/{page_name}",
            "sources": [],
            "related": [],
            "content": f"Evidence from {page_name}, {heading}",
        },
    }


def test_assemble_wiki_results_replaces_duplicate_page_slots() -> None:
    results = [
        _wiki_result("pesticides-foodex2.md", 1, "Domain"),
        _wiki_result("pesticides-foodex2.md", 2, "Worked Signals"),
        _wiki_result("pesticides-foodex2.md", 3, "Validation"),
        _wiki_result("base-term-selection.md", 4, "Base Term"),
        _wiki_result("term-type-facet-constraints.md", 5, "Legality"),
    ]

    formatted, trace = qdrant_ask._assemble_wiki_results(results, page_limit=3)

    assert [item["pages_used"] for item in formatted] == [
        "pesticides-foodex2.md",
        "base-term-selection.md",
        "term-type-facet-constraints.md",
    ]
    assert trace["candidate_chunk_count"] == 5
    assert trace["candidate_unique_page_count"] == 3
    assert trace["selected_page_count"] == 3
    assert trace["duplicate_chunk_count"] == 2
    assert trace["candidate_duplicate_ratio"] == 0.4
    assert trace["preassembly_duplicate_slot_waste"] == 2 / 3
    assert trace["duplicate_slot_waste"] == 0.0
    assert len(trace["dropped_duplicate_chunks"]) == 2


def test_retrieve_wiki_context_oversamples_and_returns_unique_pages(
    monkeypatch,
) -> None:
    search_limits: list[int] = []

    monkeypatch.setattr(
        qdrant_ask,
        "_query_embedding",
        lambda **kwargs: ([0.1, 0.2], {"total_tokens": 4}, 7),
    )

    def fake_search(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        search_limits.append(kwargs["limit"])
        return (
            [
                _wiki_result("pesticides-foodex2.md", 1, "Domain"),
                _wiki_result("pesticides-foodex2.md", 2, "Worked Signals"),
                _wiki_result("base-term-selection.md", 3, "Base Term"),
                _wiki_result("term-type-facet-constraints.md", 4, "Legality"),
            ],
            5,
        )

    monkeypatch.setattr(qdrant_ask, "_search_qdrant", fake_search)

    context = qdrant_ask.retrieve_qdrant_ask_context(
        question="Fresh grapes; reporting domain: pesticides",
        retrieval_mode="wiki",
        limit=3,
        retrieval_strategy="diverse_pages",
    )

    assert search_limits == [30]
    assert context["pages_used"] == [
        "pesticides-foodex2.md",
        "base-term-selection.md",
        "term-type-facet-constraints.md",
    ]
    assert len(context["answerer_pages"]) == 3
    assert len(context["page_summaries"]) == 3
    assert context["retrieval"]["limit"] == 3
    assert context["retrieval"]["strategy"] == "diverse_pages"
    assert context["retrieval"]["candidate_limit"] == 30
    assert context["retrieval"]["result_count"] == 4
    assert context["retrieval"]["selected_result_count"] == 3


def test_source_context_keeps_existing_top_k_semantics(monkeypatch) -> None:
    search_limits: list[int] = []
    monkeypatch.setattr(
        qdrant_ask,
        "_query_embedding",
        lambda **kwargs: ([0.1, 0.2], {}, 7),
    )

    def fake_search(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        search_limits.append(kwargs["limit"])
        return (
            [
                {
                    "score": 0.9,
                    "payload": {
                        "source_file": "guidance.pdf",
                        "source_path": "docs/guidance.pdf",
                        "location": "page 1",
                        "content": "First source chunk",
                    },
                },
                {
                    "score": 0.8,
                    "payload": {
                        "source_file": "guidance.pdf",
                        "source_path": "docs/guidance.pdf",
                        "location": "page 2",
                        "content": "Second source chunk",
                    },
                },
            ],
            5,
        )

    monkeypatch.setattr(qdrant_ask, "_search_qdrant", fake_search)

    context = qdrant_ask.retrieve_qdrant_ask_context(
        question="Source question",
        retrieval_mode="source",
        limit=2,
    )

    assert search_limits == [2]
    assert len(context["answerer_pages"]) == 2
    assert context["pages_used"] == ["guidance.pdf"]
    assert context["retrieval"]["candidate_limit"] == 2
    assert context["retrieval"]["strategy"] == "legacy_topk"
    assert "assembly" not in context["retrieval"]


def test_wiki_context_defaults_to_legacy_top_k(monkeypatch) -> None:
    search_limits: list[int] = []
    monkeypatch.delenv("WIKI_RAG_RETRIEVAL_STRATEGY", raising=False)
    monkeypatch.setattr(
        qdrant_ask,
        "_query_embedding",
        lambda **kwargs: ([0.1, 0.2], {}, 7),
    )

    def fake_search(**kwargs: Any) -> tuple[list[dict[str, Any]], int]:
        search_limits.append(kwargs["limit"])
        return (
            [
                _wiki_result("pesticides-foodex2.md", 1, "Domain"),
                _wiki_result("pesticides-foodex2.md", 2, "Worked Signals"),
            ],
            5,
        )

    monkeypatch.setattr(qdrant_ask, "_search_qdrant", fake_search)

    context = qdrant_ask.retrieve_qdrant_ask_context(
        question="Fresh grapes",
        retrieval_mode="wiki",
        limit=2,
    )

    assert search_limits == [2]
    assert len(context["answerer_pages"]) == 2
    assert context["pages_used"] == ["pesticides-foodex2.md"]
    assert context["retrieval"]["strategy"] == "legacy_topk"
    assert "assembly" not in context["retrieval"]
