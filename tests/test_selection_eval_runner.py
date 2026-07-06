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
)

CASE = {"id": "T-0001", "reviewed": True, "labels": {"must_have": ["a.md"], "acceptable": [], "must_not": []}}


def test_build_context_pack_row_extracts_pack_chars_and_enforcement():
    response = {
        "pages": [{"content": "abcde"}, {"content": "xyz"}],
        "trace": {
            "skeleton_enforcement": {
                "backfilled": [{"page": "b.md"}],
                "dropped": [{"page": "c.md"}],
            },
            "token_summary": {"total_tracked_tokens": 42},
        },
    }
    row = _build_context_pack_row(CASE, response, ["a.md"])
    assert row["pack_chars"] == 8
    assert row["backfilled"] == [{"page": "b.md"}]
    assert row["dropped"] == [{"page": "c.md"}]
    assert row["selector_tokens"] == {"total_tracked_tokens": 42}


def test_build_context_pack_row_requires_skeleton_enforcement():
    response = {"pages": [], "trace": {}}
    with pytest.raises(RuntimeError, match="skeleton_enforcement"):
        _build_context_pack_row(CASE, response, ["a.md"])


def test_build_ask_row_returns_no_context_pack_only_fields():
    response = {
        "answer": "some answer",
        "citations": [],
        "pages_used": ["a.md"],
        "trace": {"index_used": True, "retrieval": {}, "answerer": {}},
    }
    row = _build_ask_row(CASE, response, ["a.md"])
    assert row == {}
    assert "pack_chars" not in row
    assert "backfilled" not in row
    assert "selector_tokens" not in row


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
    def fake_urlopen(req, timeout=180):
        return _FakeResponse(
            {
                "answer": "the answer",
                "citations": [],
                "pages_used": ["a.md"],
                "trace": {"index_used": True},
            }
        )

    monkeypatch.setattr("scripts.selection_eval.urllib.request.urlopen", fake_urlopen)

    cases = [{**CASE, "request": {"question": "q", "max_pages": 6}}]
    rows, summary = run_pass(cases, "http://fake", 1, endpoint="ask")

    assert rows[0]["pages_used"] == ["a.md"]
    assert "backfilled" not in rows[0]
    assert "pack_chars" not in rows[0]
    assert "mean_pack_chars" not in summary
    assert "backfill_case_rate" not in summary
    assert "mean_selector_tokens" not in summary
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
