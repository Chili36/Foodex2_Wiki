from __future__ import annotations

import json
from pathlib import Path

from wiki_api.librarian import (
    AnthropicFoodEx2Solver,
    AnthropicWikiLibrarian,
    AnthropicWikiPageSelector,
)
from wiki_api.wiki_store import WikiStore


def _response(*, stop_reason: str, content: list[dict[str, object]], input_tokens: int, output_tokens: int):
    return {
        "stop_reason": stop_reason,
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


class FakeMessages:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self._responses[len(self.calls) - 1]


class FakeAnthropicClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.messages = FakeMessages(responses)


def _store() -> WikiStore:
    return WikiStore(Path("/Users/davidfoster/Dev/LLM Knowledge Base"))


def test_librarian_batches_page_reads() -> None:
    final_payload = {
        "pages_used": ["ignored-by-wrapper"],
        "query_classification": {
            "food_type": "composite",
            "domain": "general_food",
            "signals": ["packaging"],
        },
        "candidate_focus": {"promising_codes": ["A044C"], "rejected_patterns": []},
        "policy_pack": {
            "base_term_rules": ["Use a composite base term."],
            "facet_rules": ["Use packaging facets when explicit."],
            "validation_rules": [],
            "domain_rules": [],
            "construction_rules": [],
            "open_questions": [],
            "wiki_gaps": [],
        },
    }
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="tool_use",
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "read_wiki_pages",
                        "input": {
                            "page_names": [
                                "base-term-selection.md",
                                "packaging-facets.md",
                            ]
                        },
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            ),
            _response(
                stop_reason="end_turn",
                content=[{"type": "text", "text": json.dumps(final_payload)}],
                input_tokens=150,
                output_tokens=75,
            ),
        ]
    )

    librarian = AnthropicWikiLibrarian(store=_store(), client=client, model="fake-model", max_pages=6)
    result = librarian.run(
        {
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {},
            "candidates": [],
            "context": {},
        }
    )

    assert result.data["pages_used"] == [
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
    ]
    assert len(result.tool_trace) == 2
    assert result.token_summary["calls"] == 2

    first_call_content = client.messages.calls[0]["messages"][0]["content"]
    assert isinstance(first_call_content, str)
    first_call_payload = json.loads(first_call_content)
    assert "wiki_index" in first_call_payload
    assert "case" in first_call_payload

    second_call_tool_result = client.messages.calls[1]["messages"][-1]["content"][0]["content"]
    tool_result_payload = json.loads(second_call_tool_result)
    assert [page["page_name"] for page in tool_result_payload["pages"]] == [
        "base-term-selection.md",
        "packaging-facets.md",
    ]
    assert tool_result_payload["skipped"] == []
    assert tool_result_payload["errors"] == []


def test_librarian_respects_total_page_cap_with_preloaded_index() -> None:
    final_payload = {
        "pages_used": [],
        "query_classification": {
            "food_type": "composite",
            "domain": "general_food",
            "signals": [],
        },
        "candidate_focus": {"promising_codes": [], "rejected_patterns": []},
        "policy_pack": {
            "base_term_rules": [],
            "facet_rules": [],
            "validation_rules": [],
            "domain_rules": [],
            "construction_rules": [],
            "open_questions": [],
            "wiki_gaps": [],
        },
    }
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="tool_use",
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "read_wiki_pages",
                        "input": {
                            "page_names": [
                                "base-term-selection.md",
                                "packaging-facets.md",
                            ]
                        },
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            ),
            _response(
                stop_reason="end_turn",
                content=[{"type": "text", "text": json.dumps(final_payload)}],
                input_tokens=150,
                output_tokens=75,
            ),
        ]
    )

    librarian = AnthropicWikiLibrarian(store=_store(), client=client, model="fake-model", max_pages=2)
    result = librarian.run(
        {
            "search_term": "test",
            "deconstructed_query": {},
            "candidates": [],
            "context": {},
        }
    )

    assert result.data["pages_used"] == ["index.md", "base-term-selection.md"]

    second_call_tool_result = client.messages.calls[1]["messages"][-1]["content"][0]["content"]
    tool_result_payload = json.loads(second_call_tool_result)
    assert [page["page_name"] for page in tool_result_payload["pages"]] == [
        "base-term-selection.md"
    ]
    assert tool_result_payload["skipped"] == [
        {
            "page_name": "packaging-facets.md",
            "reason": "page_limit_exceeded",
            "limit": 2,
        }
    ]


def test_page_selector_returns_pages_without_policy_synthesis_turn() -> None:
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="tool_use",
                content=[
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "read_wiki_pages",
                        "input": {
                            "page_names": [
                                "base-term-selection.md",
                                "packaging-facets.md",
                            ]
                        },
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            )
        ]
    )

    selector = AnthropicWikiPageSelector(store=_store(), client=client, model="fake-model", max_pages=6)
    result = selector.run(
        {
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {},
            "candidates": [],
            "context": {},
        }
    )

    assert result.pages_used == [
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
    ]
    assert len(result.tool_trace) == 2
    assert result.token_summary["calls"] == 1
    assert len(client.messages.calls) == 1


def test_page_selector_accepts_direct_json_page_names_without_tool() -> None:
    client = FakeAnthropicClient(
        [
            _response(
                stop_reason="end_turn",
                content=[
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"page_names": ["base-term-selection.md", "packaging-facets.md"]}
                        ),
                    }
                ],
                input_tokens=100,
                output_tokens=25,
            )
        ]
    )

    selector = AnthropicWikiPageSelector(store=_store(), client=client, model="fake-model", max_pages=6)
    result = selector.run(
        {
            "search_term": "test",
            "deconstructed_query": {},
            "candidates": [],
            "context": {},
        }
    )

    assert result.pages_used == [
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
    ]
    assert result.token_summary["calls"] == 1


def test_librarian_prefers_policy_model_env(monkeypatch) -> None:
    monkeypatch.setenv("WIKI_LIBRARIAN_MODEL", "shared-model")
    monkeypatch.setenv("WIKI_POLICY_MODEL", "policy-model")
    client = FakeAnthropicClient([])

    librarian = AnthropicWikiLibrarian(store=_store(), client=client)

    assert librarian.model == "policy-model"


def test_selector_falls_back_to_shared_model_env(monkeypatch) -> None:
    monkeypatch.delenv("WIKI_CONTEXT_MODEL", raising=False)
    monkeypatch.setenv("WIKI_LIBRARIAN_MODEL", "shared-model")
    client = FakeAnthropicClient([])

    selector = AnthropicWikiPageSelector(store=_store(), client=client)

    assert selector.model == "shared-model"


def test_store_extracts_guiding_principles_from_index() -> None:
    principles = _store().guiding_principles()

    assert len(principles) >= 4
    assert any("top-down" in principle for principle in principles)


def test_store_cleans_page_content_for_model() -> None:
    store = _store()
    page = store.read_page("base-term-selection.md")
    cleaned = store.clean_content_for_model(page)

    assert cleaned.startswith("# Base Term Selection")
    assert "<!-- Source:" not in cleaned
    assert "(EFSA guidance p42; Training p5)" not in cleaned


def test_solver_prefers_solver_model_env(monkeypatch) -> None:
    monkeypatch.setenv("WIKI_LIBRARIAN_MODEL", "shared-model")
    monkeypatch.setenv("WIKI_POLICY_MODEL", "policy-model")
    monkeypatch.setenv("WIKI_SOLVER_MODEL", "solver-model")
    client = FakeAnthropicClient([])

    solver = AnthropicFoodEx2Solver(client=client)

    assert solver.model == "solver-model"


def test_solver_does_not_inherit_policy_model_env(monkeypatch) -> None:
    monkeypatch.setenv("WIKI_LIBRARIAN_MODEL", "shared-model")
    monkeypatch.setenv("WIKI_POLICY_MODEL", "policy-model")
    monkeypatch.delenv("WIKI_SOLVER_MODEL", raising=False)
    client = FakeAnthropicClient([])

    solver = AnthropicFoodEx2Solver(client=client)

    assert solver.model == "shared-model"
