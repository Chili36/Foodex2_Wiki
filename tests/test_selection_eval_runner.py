"""Unit tests for scripts/selection_eval.py runner logic that don't need HTTP.

Covers: the ask-vs-context-pack row-building branch (via stubbed response
dicts, no network call) and the effective_max_pages provenance computation.
"""
from __future__ import annotations

import pytest

from scripts.selection_eval import (
    _build_ask_row,
    _build_context_pack_row,
    effective_max_pages,
    median_summary,
    run_pass,
    validate_eval_budget,
)

CASE = {"id": "T-0001", "reviewed": True, "labels": {"must_have": ["a.md"], "acceptable": [], "must_not": []}}


def test_build_context_pack_row_extracts_pack_chars_and_enforcement():
    response = {
        "pages": [{"content": "abcde"}, {"content": "xyz"}],
        "trace": {
            "skeleton_enforcement": {
                "backfilled": [{"page": "b.md"}],
                "dropped": [{"page": "c.md"}],
                "trimmed": ["index.md"],
            },
            "token_summary": {"total_tracked_tokens": 42},
            "timing_summary": {"request_wall_time_ms": 1234},
        },
    }
    row = _build_context_pack_row(CASE, response, ["a.md"])
    assert row["pack_chars"] == 8
    assert row["backfilled"] == [{"page": "b.md"}]
    assert row["dropped"] == [{"page": "c.md"}]
    assert row["trimmed"] == ["index.md"]
    assert row["selector_tokens"] == {"total_tracked_tokens": 42}
    assert row["selector_wall_time_ms"] == 1234


def test_build_context_pack_row_requires_skeleton_enforcement():
    response = {"pages": [], "trace": {}}
    with pytest.raises(RuntimeError, match="skeleton_enforcement"):
        _build_context_pack_row(CASE, response, ["a.md"])


def test_build_ask_row_records_selector_usage_without_context_pack_fields():
    response = {
        "answer": "some answer",
        "citations": [],
        "pages_used": ["a.md"],
        "trace": {
            "index_used": True,
            "retrieval": {"token_summary": {"total_tracked_tokens": 42}},
            "total": {"request_wall_time_ms": 1234},
        },
    }
    row = _build_ask_row(CASE, response, ["a.md"])
    assert row == {
        "selector_tokens": {"total_tracked_tokens": 42},
        "selector_wall_time_ms": 1234,
    }
    assert "pack_chars" not in row
    assert "backfilled" not in row


def test_build_ask_row_requires_selector_usage_trace():
    with pytest.raises(RuntimeError, match="retrieval token_summary"):
        _build_ask_row(CASE, {"trace": {}}, ["a.md"])


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self):
        import json

        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_run_pass_ask_mode_skips_context_pack_only_metrics(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=180):
        import json

        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse(
            {
                "answer": "the answer",
                "citations": [],
                "pages_used": ["a.md"],
                "trace": {
                    "index_used": True,
                    "retrieval": {"token_summary": {"total_tracked_tokens": 42}},
                    "total": {"request_wall_time_ms": 1234},
                },
            }
        )

    monkeypatch.setattr("scripts.selection_eval.urllib.request.urlopen", fake_urlopen)

    cases = [{**CASE, "request": {"question": "q", "max_pages": 6}}]
    rows, summary = run_pass(
        cases,
        "http://fake",
        1,
        endpoint="ask",
        selector_model_override="gpt-5.6-terra",
    )

    assert rows[0]["pages_used"] == ["a.md"]
    assert rows[0]["selector_model_sent"] == "gpt-5.6-terra"
    assert captured["body"]["selector_model"] == "gpt-5.6-terra"
    assert "backfilled" not in rows[0]
    assert "pack_chars" not in rows[0]
    assert "mean_pack_chars" not in summary
    assert "backfill_case_rate" not in summary
    assert summary["mean_selector_tokens"] == 42
    assert summary["mean_selector_wall_time_ms"] == 1234
    # Core recall/precision metrics are still present (shared aggregate()).
    assert "mean_must_have_recall" in summary


def test_run_pass_context_pack_mode_still_requires_skeleton_enforcement(monkeypatch):
    def fake_urlopen(req, timeout=180):
        return _FakeResponse(
            {
                "pages_used": ["a.md"],
                "pages": [],
                "trace": {},
            }
        )

    monkeypatch.setattr("scripts.selection_eval.urllib.request.urlopen", fake_urlopen)

    cases = [{**CASE, "request": {"max_pages": 9}}]
    with pytest.raises(RuntimeError, match="skeleton_enforcement"):
        run_pass(cases, "http://fake", 1, endpoint="context-pack")


def test_median_summary_omits_metrics_missing_from_a_mode():
    passes = [
        {"summary": {"mean_must_have_recall": 1.0, "mean_precision": 1.0, "leak_free_rate": 1.0}},
        {"summary": {"mean_must_have_recall": 0.5, "mean_precision": 0.5, "leak_free_rate": 0.0}},
    ]
    medians = median_summary(passes)
    assert "mean_must_have_recall" in medians
    assert "mean_pack_chars" not in medians
    assert medians["passes"] == 2


def test_effective_max_pages_uses_override_when_present():
    cases = [
        {"request": {"max_pages": 6}},
        {"request": {"max_pages": 9}},
    ]
    assert effective_max_pages(cases, 5) == {"min": 5, "max": 5}


def test_effective_max_pages_falls_back_to_per_case_request():
    cases = [
        {"request": {"max_pages": 6}},
        {"request": {"max_pages": 9}},
    ]
    assert effective_max_pages(cases, None) == {"min": 6, "max": 9}


def test_effective_max_pages_handles_missing_values():
    cases = [{"request": {}}]
    assert effective_max_pages(cases, None) == {"min": None, "max": None}


def test_call_ask_uses_selector_only_endpoint_and_strips_answerer_fields(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        import io
        import json as _json
        captured["body"] = _json.loads(req.data.decode("utf-8"))
        captured["url"] = req.full_url

        class _Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return _Resp(b'{"pages_used": [], "trace": {}}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    from scripts.selection_eval import call_ask

    call_ask(
        "http://x",
        {
            "question": "q",
            "use_graph_expansion": True,
            "answerer_model": "claude-sonnet-4-6",
        },
    )
    assert captured["url"] == "http://x/wiki/ask/select-pages"
    assert "use_graph_expansion" not in captured["body"]
    assert "answerer_model" not in captured["body"]


def test_eval_budget_rejects_unacknowledged_high_repeats():
    with pytest.raises(ValueError, match="allow-high-repeats"):
        validate_eval_budget(case_count=39, repeats=5)


def test_eval_budget_rejects_call_count_above_cap():
    with pytest.raises(ValueError, match="estimated 240 LLM calls"):
        validate_eval_budget(case_count=80, repeats=3, max_estimated_calls=200)


def test_eval_budget_accepts_explicit_high_repeat_run_within_cap():
    assert validate_eval_budget(
        case_count=39,
        repeats=5,
        max_estimated_calls=200,
        allow_high_repeats=True,
    ) == 195
