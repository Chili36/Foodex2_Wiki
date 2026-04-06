from __future__ import annotations

import asyncio

import httpx

import wiki_api.app as app_module
from wiki_api.librarian import LibrarianResult, PageSelectionResult, SolverResult


async def _request(method: str, path: str, **kwargs: object) -> httpx.Response:
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **kwargs)


def request(method: str, path: str, **kwargs: object) -> httpx.Response:
    return asyncio.run(_request(method, path, **kwargs))


class FakeLibrarian:
    def __init__(self) -> None:
        self.max_pages = 6
        self.model = "fake-claude"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> LibrarianResult:
        self.calls.append(payload)
        return LibrarianResult(
            data={
                "pages_used": [
                    "index.md",
                    "base-term-selection.md",
                    "packaging-facets.md",
                    "ingredient-facets.md",
                ],
                "query_classification": {
                    "food_type": "composite",
                    "domain": "general_food",
                    "signals": ["ingredients", "packaging"],
                    "candidate_term_types": ["f", "s"],
                },
                "candidate_focus": {
                    "promising_codes": ["A044C"],
                    "rejected_patterns": ["Do not use facet terms as base terms."],
                },
                "policy_pack": {
                    "base_term_rules": ["base-term-selection.md: Use a composite base term for recipe foods."],
                    "facet_rules": ["packaging-facets.md: If the query says glass jar, split it into F18 jar and F19 glass."],
                    "validation_rules": ["term-type-facet-constraints.md: Composite terms use F04, not F01 or F27."],
                    "domain_rules": [],
                    "construction_rules": ["code-string-format.md: Use base#facet.code$facet.code syntax."],
                    "open_questions": [
                        "Packaging detail may justify F18/F19, but packaging alone does not prove a preservation process."
                    ],
                    "wiki_gaps": [],
                },
            },
            tool_trace=[
                {"page_name": "index.md", "order": 1, "chars": 100, "synthetic": False},
                {"page_name": "base-term-selection.md", "order": 2, "chars": 100, "synthetic": False},
                {"page_name": "packaging-facets.md", "order": 3, "chars": 100, "synthetic": False},
                {"page_name": "ingredient-facets.md", "order": 4, "chars": 100, "synthetic": False},
            ],
            token_summary={
                "model": "fake-claude",
                "calls": 2,
                "input_tokens": 120,
                "output_tokens": 80,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 200,
                "per_call": [
                    {
                        "stop_reason": "tool_use",
                        "input_tokens": 60,
                        "output_tokens": 40,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 100,
                    },
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 60,
                        "output_tokens": 40,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 100,
                    },
                ],
            },
            timing_summary={
                "calls": 2,
                "llm_time_ms": 1420,
                "librarian_wall_time_ms": 1600,
                "per_call": [
                    {"call_number": 1, "duration_ms": 700, "stop_reason": "tool_use"},
                    {"call_number": 2, "duration_ms": 720, "stop_reason": "end_turn"},
                ],
            },
        )


class FakeSelector:
    def __init__(self) -> None:
        self.max_pages = 6
        self.model = "fake-claude"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        self.calls.append(payload)
        return PageSelectionResult(
            pages_used=[
                "index.md",
                "base-term-selection.md",
                "packaging-facets.md",
                "ingredient-facets.md",
            ],
            tool_trace=[
                {"page_name": "base-term-selection.md", "order": 1, "chars": 100, "synthetic": False},
                {"page_name": "packaging-facets.md", "order": 2, "chars": 100, "synthetic": False},
                {"page_name": "ingredient-facets.md", "order": 3, "chars": 100, "synthetic": False},
            ],
            token_summary={
                "model": "fake-claude",
                "calls": 1,
                "input_tokens": 90,
                "output_tokens": 20,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 110,
                "per_call": [
                    {
                        "stop_reason": "tool_use",
                        "input_tokens": 90,
                        "output_tokens": 20,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 110,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 640,
                "selector_wall_time_ms": 700,
                "per_call": [
                    {"call_number": 1, "duration_ms": 640, "stop_reason": "tool_use"},
                ],
            },
        )


class FakeSolver:
    def __init__(self) -> None:
        self.model = "fake-claude-solver"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> SolverResult:
        self.calls.append(payload)
        return SolverResult(
            data={
                "selectedCode": "A044C",
                "selectedName": "Tomato-containing cooked sauces",
                "selectedTermType": "s",
                "constructedCode": "A044C#F04.A00VV$F04.A00GZ$F18.A07NN$F19.A07PF",
                "reasoning": "Selected the composite tomato sauce term and added basil, garlic, jar, and glass as explicit refinements.",
                "implicitFacets": [
                    {"facetType": "F04", "facetCode": "A0DMX", "facetMeaning": "Tomatoes"}
                ],
                "suggestedExplicitFacets": [
                    {"facetType": "F04", "facetCode": "A00VV", "facetMeaning": "Basil"},
                    {"facetType": "F04", "facetCode": "A00GZ", "facetMeaning": "Garlic"},
                    {"facetType": "F18", "facetCode": "A07NN", "facetMeaning": "Jar"},
                    {"facetType": "F19", "facetCode": "A07PF", "facetMeaning": "Glass"},
                ],
                "validationCheck": {
                    "passes": True,
                    "rulesConsulted": ["BR03", "BR04"],
                    "warnings": [],
                },
                "alternativeCodes": [
                    {
                        "code": "A044P",
                        "name": "Tomato ketchup and related sauces",
                        "reason": "Tomato sauce family fit, but weaker than cooked sauces.",
                    }
                ],
                "confidence": 0.95,
                "regulatoryNotes": "Carry the base-term monitoring flags unchanged.",
            },
            token_summary={
                "model": "fake-claude-solver",
                "calls": 1,
                "input_tokens": 300,
                "output_tokens": 120,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 420,
                "per_call": [
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 300,
                        "output_tokens": 120,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 420,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 910,
                "solver_wall_time_ms": 950,
                "per_call": [
                    {"call_number": 1, "duration_ms": 910, "stop_reason": "end_turn"},
                ],
            },
        )


def setup_function() -> None:
    app_module.librarian_runner = FakeLibrarian()
    app_module.selector_runner = FakeSelector()
    app_module.solver_runner = FakeSolver()


def test_health() -> None:
    response = request("GET", "/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_pages_includes_packaging() -> None:
    response = request("GET", "/wiki/pages")
    assert response.status_code == 200
    payload = response.json()
    names = {page["page_name"] for page in payload["pages"]}
    assert "packaging-facets.md" in names


def test_get_unknown_page_returns_404() -> None:
    response = request("GET", "/wiki/pages/not-a-real-page.md")
    assert response.status_code == 404


def test_policy_pack_uses_librarian_response() -> None:
    response = request(
        "POST",
        "/wiki/policy-pack",
        json={
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {
                "raw_query": "Tomato basil and garlic sauce in a glass jar",
                "base_term": "tomato basil and garlic sauce",
                "components": [
                    {"text": "sauce", "kind": "PROCESS"},
                    {"text": "glass jar", "kind": "PACKAGING"},
                ],
            },
            "candidates": [
                {"code": "A044C", "name": "Tomato-containing cooked sauces", "termType": "s"},
                {"code": "A07NN", "name": "Jar", "termType": "f"},
                {"code": "A07PF", "name": "Glass", "termType": "f"},
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["guiding_principles"]) >= 4
    assert payload["guiding_principles"][1].startswith("FoodEx2 is built top-down.")
    assert payload["pages_used"] == [
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
        "ingredient-facets.md",
    ]
    assert payload["trace"]["selection_method"] == "service-owned llm librarian"
    assert payload["trace"]["model"] == "fake-claude"
    assert payload["trace"]["token_summary"]["total_tracked_tokens"] == 200
    assert payload["trace"]["timing_summary"]["llm_time_ms"] == 1420
    assert payload["trace"]["timing_summary"]["librarian_wall_time_ms"] == 1600
    assert payload["trace"]["timing_summary"]["request_wall_time_ms"] >= 0
    assert payload["query_classification"]["food_type"] == "composite"
    assert payload["pages"][2]["page_name"] == "packaging-facets.md"


def test_context_pack_returns_only_pages_and_trace() -> None:
    response = request(
        "POST",
        "/wiki/context-pack",
        json={
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {
                "raw_query": "Tomato basil and garlic sauce in a glass jar",
            },
            "candidates": [
                {"code": "A044C", "name": "Tomato-containing cooked sauces", "termType": "s"},
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["guiding_principles"]) >= 4
    assert payload["guiding_principles"][2].startswith("FoodEx2 prefers modular description")
    assert payload["pages_used"] == [
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
        "ingredient-facets.md",
    ]
    assert "policy_pack" not in payload
    assert "query_classification" not in payload
    assert payload["trace"]["selection_method"] == "service-owned llm page selector"
    assert payload["trace"]["token_summary"]["calls"] == 1
    assert payload["trace"]["timing_summary"]["llm_time_ms"] == 640
    assert payload["trace"]["timing_summary"]["selector_wall_time_ms"] == 700
    assert payload["trace"]["timing_summary"]["request_wall_time_ms"] >= 0
    assert payload["pages"][0]["page_name"] == "index.md"


def test_solve_returns_final_code_and_stage_traces() -> None:
    response = request(
        "POST",
        "/wiki/solve",
        json={
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {
                "raw_query": "Tomato basil and garlic sauce in a glass jar",
            },
            "candidates": [
                {"code": "A044C", "name": "Tomato-containing cooked sauces", "termType": "s"},
                {"code": "A00VV", "name": "Basil", "termType": "r"},
                {"code": "A00GZ", "name": "Garlic", "termType": "r"},
                {"code": "A07NN", "name": "Jar", "termType": "f"},
                {"code": "A07PF", "name": "Glass", "termType": "f"},
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["solution"]["constructedCode"] == "A044C#F04.A00VV$F04.A00GZ$F18.A07NN$F19.A07PF"
    assert payload["solution"]["validationCheck"]["passes"] is True
    assert payload["solution"]["confidence"] == 5
    assert payload["trace"]["selection_method"] == "service-owned llm librarian + solver"
    assert payload["trace"]["retrieval"]["model"] == "fake-claude"
    assert payload["trace"]["solver"]["model"] == "fake-claude-solver"
    assert payload["trace"]["total"]["total_llm_calls"] == 3
    assert payload["trace"]["total"]["total_tracked_tokens"] == 620
    assert len(payload["guiding_principles"]) >= 4


def test_solve_requires_candidates() -> None:
    response = request(
        "POST",
        "/wiki/solve",
        json={
            "search_term": "orange nectar",
            "deconstructed_query": {},
            "candidates": [],
            "context": {},
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "solve requires a non-empty candidates list"
