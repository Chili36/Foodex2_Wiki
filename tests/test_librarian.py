from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import wiki_api.librarian as librarian_module
from wiki_api.librarian import (
    AnthropicFoodEx2Solver,
    AnthropicWikiLibrarian,
    AnthropicWikiPageSelector,
    OpenAICompatibleMessagesClient,
    infer_model_provider,
)
from wiki_api.wiki_store import WikiStore

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


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
    return WikiStore(REPO_ROOT)


def test_infer_model_provider_for_ask_overrides() -> None:
    assert infer_model_provider("claude-haiku-4-5") == "anthropic"
    assert infer_model_provider("gemini-3.5-flash") == "gemini"
    assert infer_model_provider("gpt-5.4-mini") == "openai"
    assert infer_model_provider("lmstudio:qwen2.5") == "lmstudio"
    assert infer_model_provider(None) == "anthropic"


def test_global_lmstudio_provider_overrides_model_inference(monkeypatch) -> None:
    monkeypatch.setenv("WIKI_LLM_PROVIDER", "lmstudio")

    assert infer_model_provider("claude-sonnet-4-6") == "lmstudio"
    assert infer_model_provider(None) == "lmstudio"


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


def test_lmstudio_global_model_is_used_for_runtime_components(monkeypatch) -> None:
    monkeypatch.setenv("WIKI_LLM_PROVIDER", "lmstudio")
    monkeypatch.setenv("WIKI_LMSTUDIO_MODEL", "local-foodex-model")
    monkeypatch.setenv("WIKI_LIBRARIAN_MODEL", "claude-sonnet-4-6")
    client = FakeAnthropicClient([])

    selector = AnthropicWikiPageSelector(store=_store(), client=client)

    assert selector.model == "local-foodex-model"


def test_lmstudio_openai_compatible_client_maps_tool_calls(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_http_post_json(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_wiki_pages",
                                    "arguments": json.dumps(
                                        {"page_names": ["base-term-selection.md"]}
                                    ),
                                },
                            }
                        ]
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

    monkeypatch.setattr(librarian_module, "_http_post_json", fake_http_post_json)
    client = OpenAICompatibleMessagesClient(base_url="http://127.0.0.1:1234/v1")

    response = client.messages.create(
        model="lmstudio:local-model",
        max_tokens=100,
        system="system text",
        tools=[
            {
                "name": "read_wiki_pages",
                "description": "Read pages.",
                "input_schema": {"type": "object", "properties": {}},
            }
        ],
        messages=[{"role": "user", "content": "Pick pages."}],
    )

    assert calls[0]["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    payload = calls[0]["payload"]
    assert payload["model"] == "local-model"
    assert payload["messages"][0] == {"role": "system", "content": "system text"}
    assert payload["tools"][0]["function"]["name"] == "read_wiki_pages"
    assert response["stop_reason"] == "tool_use"
    assert response["content"][0]["input"] == {"page_names": ["base-term-selection.md"]}


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

    vmpr_page = store.read_page("vmpr-legislative-mapping.md")
    vmpr_cleaned = store.clean_content_for_model(vmpr_page)
    assert "(VMPR mapping p3-6)" not in vmpr_cleaned
    assert "(VMPR mapping p4)" not in vmpr_cleaned


def test_store_catalog_pages_have_summaries_and_categories() -> None:
    store = _store()
    pages = store.catalog()

    assert [page.name for page in pages if not page.summary] == []
    assert [page.name for page in pages if store.page_category(page.name) == "unknown"] == []


def test_served_wikilinks_are_extensionless() -> None:
    store = _store()
    offenders: list[str] = []
    for page in store.catalog():
        references = [*page.related, *WIKILINK_RE.findall(page.body)]
        for reference in references:
            target = reference.strip()
            if target.startswith("[[") and target.endswith("]]"):
                target = target[2:-2]
            target = target.split("|", 1)[0].split("#", 1)[0].strip()
            if target.endswith(".md"):
                offenders.append(f"{page.name}: {target}")

    assert offenders == []


def test_store_projects_context_pack_content_for_runtime_prompts() -> None:
    store = _store()
    page = store.read_page("RUNTIME_RULES.md")
    projected = store.prompt_content_for_context_pack(page)

    assert projected is not None
    assert projected.startswith("## Core Decision Order")
    assert "# Runtime Rules" not in projected
    assert "compact prompt-facing rules file" not in projected
    assert "Use it as the always-on runtime layer" not in projected
    assert "## Supporting Pages By Signal" not in projected


def test_context_pack_projection_omits_examples_and_large_reference_catalogs() -> None:
    store = _store()
    process_page = store.read_page("process-facets.md")
    projected_process = store.prompt_content_for_context_pack(process_page)

    assert projected_process is not None
    assert "## Rule Of Use" in projected_process
    assert "## Appendix A2 Codes" not in projected_process
    assert "A07KT portioning" not in projected_process
    assert "## Worked Examples" not in projected_process

    base_page = store.read_page("base-term-selection.md")
    projected_base = store.prompt_content_for_context_pack(base_page)
    assert projected_base is not None
    assert "## Worked Examples" not in projected_base
    assert "kangaroo fresh fat tissue" not in projected_base

    facet_page = store.read_page("facet-coding-rules.md")
    projected_facet = store.prompt_content_for_context_pack(facet_page)
    assert projected_facet is not None
    assert "## Facet Category Reference" in projected_facet
    assert "`F21` | Production method or growing condition" in projected_facet
    assert "under-glass growing" in projected_facet
    assert "## Worked Examples" not in projected_facet


def test_domoic_acid_scallops_lookup_is_prompt_ready() -> None:
    store = _store()
    page = store.read_page("domoic-acid-scallops.md")
    projected = store.prompt_content_for_context_pack(page)

    assert store.page_category(page.name) == "domain_overlay"
    assert projected is not None
    assert "## Reporting Rule" in projected
    assert "origFishAreaCode" in projected
    assert "`A16FR#F01.A055P$F20.A18FH`" in projected
    assert "Pecten maximus, Hepatopancreas" in projected
    assert "Do not invent a scallop species" in projected

    with (REPO_ROOT / "foodex2_docs" / "domoic_acid_scallops_mtx.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 60
    assert {
        "scientific_name": "Pecten maximus",
        "part_of_scallops": "Hepatopancreas",
        "sampMatCode": "A16FR#F01.A055P$F20.A18FH",
        "sampMatText": "Pecten maximus, Hepatopancreas",
    }.items() <= rows[34].items()


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
