from __future__ import annotations

import json

import pytest

from scripts.wiki_ragas_eval import (
    build_endpoint_payload,
    deterministic_scores,
    estimated_budget,
    load_cases,
    response_contexts,
    summarize,
)


def test_load_cases_validates_and_filters_reviewed(tmp_path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {"id": "DMT-001", "reviewed": True, "question": "Question one?"},
                    {"id": "DMT-002", "reviewed": False, "question": "Question two?"},
                ],
            }
        )
    )

    assert [case["id"] for case in load_cases(path, only_reviewed=True)] == [
        "DMT-001"
    ]


def test_load_cases_rejects_duplicate_ids(tmp_path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            {
                "cases": [
                    {"id": "DMT-001", "question": "One?"},
                    {"id": "DMT-001", "question": "Two?"},
                ]
            }
        )
    )

    with pytest.raises(ValueError, match="duplicate case id"):
        load_cases(path)


def test_build_ask_payload_holds_selector_fixed() -> None:
    payload = build_endpoint_payload(
        endpoint="ask",
        case={"question": "How should this be coded?"},
        answerer_model="lmstudio:gpt-oss-120b",
        selector_model="claude-sonnet-5",
        max_pages=7,
        rag_limit=9,
        rag_strategy="diverse_pages",
        use_graph_expansion=True,
    )

    assert payload == {
        "question": "How should this be coded?",
        "answerer_model": "lmstudio:gpt-oss-120b",
        "include_page_content": True,
        "selector_model": "claude-sonnet-5",
        "max_pages": 7,
        "use_graph_expansion": True,
    }


def test_build_payload_uses_explicit_request_question() -> None:
    payload = build_endpoint_payload(
        endpoint="ask-rag",
        case={
            "question": "Anything I should think about when reporting grapes?",
            "request_question": (
                "Anything I should think about when reporting grapes? "
                "Reporting domain: pesticides."
            ),
        },
        answerer_model="model-a",
        selector_model="claude-sonnet-5",
        max_pages=7,
        rag_limit=7,
        rag_strategy="diverse_pages",
        use_graph_expansion=True,
    )

    assert payload["question"].endswith("Reporting domain: pesticides.")


def test_build_ask_rag_payload_uses_same_answerer() -> None:
    payload = build_endpoint_payload(
        endpoint="ask-rag",
        case={"question": "How should this be coded?"},
        answerer_model="lmstudio:gpt-oss-120b",
        selector_model="claude-sonnet-5",
        max_pages=7,
        rag_limit=9,
        rag_strategy="diverse_pages",
        use_graph_expansion=True,
    )

    assert payload == {
        "question": "How should this be coded?",
        "answerer_model": "lmstudio:gpt-oss-120b",
        "include_page_content": True,
        "retrieval_mode": "wiki",
        "retrieval_strategy": "diverse_pages",
        "limit": 9,
    }


def test_response_contexts_uses_content_then_summary() -> None:
    response = {
        "pages": [
            {"page_name": "one.md", "content": "Full content", "summary": "ignored"},
            {"page_name": "two.md", "content": None, "summary": "Summary only"},
            {"page_name": "three.md", "content": None, "summary": None},
        ]
    }

    assert response_contexts(response) == [
        "Page: one.md\nFull content",
        "Page: two.md\nSummary only",
    ]


def test_deterministic_scores_page_and_answer_assertions() -> None:
    case = {
        "reference_pages": ["base.md", "facets.md"],
        "must_not_pages": ["maintenance-*"],
        "required_answer_terms": ["minor ingredient"],
        "forbidden_answer_terms": ["always prohibited"],
    }
    response = {
        "pages_used": ["base.md", "maintenance-2024.md"],
        "answer": "F04 may describe a minor ingredient.",
    }

    scores = deterministic_scores(case, response)

    assert scores["reference_page_precision"] == 0.5
    assert scores["reference_page_recall"] == 0.5
    assert scores["missing_reference_pages"] == ["facets.md"]
    assert scores["prohibited_page_hits"] == ["maintenance-2024.md"]
    assert scores["deterministic_answer_pass"] is True
    assert scores["prohibited_page_pass"] is False


def test_deterministic_scores_do_not_auto_pass_unlabelled_case() -> None:
    scores = deterministic_scores(
        {
            "reference_pages": [],
            "must_not_pages": [],
            "required_answer_terms": [],
            "forbidden_answer_terms": [],
        },
        {"pages_used": ["anything.md"], "answer": "Anything"},
    )

    assert "deterministic_answer_pass" not in scores
    assert "prohibited_page_pass" not in scores


def test_estimated_budget_is_full_endpoint_model_matrix() -> None:
    assert estimated_budget(10, 2, 3, 2, 2) == {
        "cases": 10,
        "endpoint_variants": 2,
        "answerer_models": 3,
        "repeats": 2,
        "estimated_endpoint_calls": 120,
        "estimated_ragas_metric_invocations": 240,
    }


def test_summarize_keeps_endpoint_and_model_separate() -> None:
    rows = [
        {
            "endpoint": "ask",
            "answerer_model": "model-a",
            "status_code": 200,
            "elapsed_ms": 100,
            "deterministic": {
                "reference_page_recall": 1.0,
                "deterministic_answer_pass": True,
            },
            "ragas": {"faithfulness": {"score": 0.8}},
        },
        {
            "endpoint": "ask",
            "answerer_model": "model-a",
            "status_code": 500,
            "elapsed_ms": 10,
            "deterministic": {},
            "ragas": {},
        },
        {
            "endpoint": "ask-rag",
            "answerer_model": "model-a",
            "status_code": 200,
            "elapsed_ms": 200,
            "deterministic": {
                "reference_page_recall": 0.5,
                "deterministic_answer_pass": False,
            },
            "ragas": {"faithfulness": {"score": 1.0}},
        },
    ]

    summaries = summarize(rows)
    ask = next(item for item in summaries if item["endpoint"] == "ask")
    ask_rag = next(item for item in summaries if item["endpoint"] == "ask-rag")

    assert ask["success_rate"] == 0.5
    assert ask["mean_reference_page_recall"] == 1.0
    assert ask["mean_ragas_faithfulness"] == 0.8
    assert ask_rag["mean_reference_page_recall"] == 0.5
    assert ask_rag["mean_deterministic_answer_pass"] == 0.0
