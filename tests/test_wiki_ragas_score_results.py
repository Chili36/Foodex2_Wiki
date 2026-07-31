from __future__ import annotations

import asyncio

from scripts import wiki_ragas_score_results


def test_score_rows_scores_successes_skips_failures_and_preserves_order(
    monkeypatch,
) -> None:
    async def fake_score_with_ragas(
        *,
        case,
        response,
        metric_names,
        judge_llm,
    ):
        await asyncio.sleep(0)
        return {
            "faithfulness": {
                "score": 1.0 if case["id"] == "DMT-001" else 0.5,
            }
        }

    monkeypatch.setattr(
        wiki_ragas_score_results,
        "score_with_ragas",
        fake_score_with_ragas,
    )
    rows = [
        {
            "repeat": 1,
            "case_id": "DMT-001",
            "answerer_model": "model-a",
            "endpoint": "ask",
            "status_code": 200,
            "answer": "Answer one",
            "pages": [{"page_name": "one.md", "content": "Context one"}],
            "ragas": {},
        },
        {
            "repeat": 1,
            "case_id": "DMT-002",
            "answerer_model": "model-a",
            "endpoint": "ask-rag",
            "status_code": 503,
            "answer": "",
            "pages": [],
            "ragas": {},
        },
    ]

    scored = asyncio.run(
        wiki_ragas_score_results.score_rows(
            rows=rows,
            cases_by_id={
                "DMT-001": {"id": "DMT-001", "question": "One?"},
                "DMT-002": {"id": "DMT-002", "question": "Two?"},
            },
            metric_names=["faithfulness"],
            judge_llm=object(),
            concurrency=2,
        )
    )

    assert [row["case_id"] for row in scored] == ["DMT-001", "DMT-002"]
    assert scored[0]["ragas"]["faithfulness"]["score"] == 1.0
    assert scored[1]["ragas"] == {}
