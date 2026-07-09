from __future__ import annotations

import asyncio

import httpx

import wiki_api.app as app_module
from wiki_api.librarian import AnswerResult, LibrarianResult, PageSelectionResult, SolverResult
from wiki_api.policy import build_policy_contract


RUNTIME_RULES_PAGE_NAME = "RUNTIME_RULES.md"


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


class FakeAnswerer:
    def __init__(self) -> None:
        self.model = "fake-claude-answerer"
        self.calls: list[dict[str, object]] = []

    def run(self, *, question: str, pages: list[dict[str, object]]) -> AnswerResult:
        self.calls.append({"question": question, "pages": pages})
        return AnswerResult(
            answer=(
                "Start by classifying the item as a derivative, then choose the most specific "
                "reportable cheese base term before considering explicit facets."
            ),
            citations=["base-term-selection.md", "implicit-vs-explicit-facets.md"],
            token_summary={
                "model": self.model,
                "calls": 1,
                "input_tokens": 210,
                "output_tokens": 80,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 290,
                "per_call": [
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 210,
                        "output_tokens": 80,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 290,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 700,
                "answerer_wall_time_ms": 760,
                "per_call": [
                    {"call_number": 1, "duration_ms": 700, "stop_reason": "end_turn"},
                ],
            },
        )


class FakeBadAnswerer:
    model = "fake-claude-answerer"

    def run(self, *, question: str, pages: list[dict[str, object]]) -> AnswerResult:
        raise ValueError("Could not extract JSON object from answerer response")


class FakeBadSolver:
    def __init__(self) -> None:
        self.model = "fake-claude-solver"

    def run(self, payload: dict[str, object]) -> SolverResult:
        raise ValueError("Could not extract JSON object from solver response")


class FakeSelector:
    def __init__(self) -> None:
        self.max_pages = 7
        self.model = "fake-claude-context"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        self.calls.append(payload)
        return PageSelectionResult(
            pages_used=[
                "index.md",
                "base-term-selection.md",
                "ingredient-facets.md",
                "packaging-facets.md",
                "term-type-facet-constraints.md",
                "implicit-vs-explicit-facets.md",
            ],
            tool_trace=[
                {"page_name": "base-term-selection.md", "order": 1, "chars": 100, "synthetic": False},
                {"page_name": "ingredient-facets.md", "order": 2, "chars": 100, "synthetic": False},
                {"page_name": "packaging-facets.md", "order": 3, "chars": 100, "synthetic": False},
                {
                    "page_name": "term-type-facet-constraints.md",
                    "order": 4,
                    "chars": 100,
                    "synthetic": False,
                },
                {
                    "page_name": "implicit-vs-explicit-facets.md",
                    "order": 5,
                    "chars": 100,
                    "synthetic": False,
                },
            ],
            token_summary={
                "model": self.model,
                "calls": 1,
                "input_tokens": 90,
                "output_tokens": 25,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 115,
                "per_call": [
                    {
                        "stop_reason": "end_turn",
                        "input_tokens": 90,
                        "output_tokens": 25,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 115,
                    }
                ],
            },
            timing_summary={
                "calls": 1,
                "llm_time_ms": 480,
                "selector_wall_time_ms": 520,
                "per_call": [
                    {"call_number": 1, "duration_ms": 480, "stop_reason": "end_turn"},
                ],
            },
        )


class FakeDomoicAcidScallopSelector:
    def __init__(self) -> None:
        self.max_pages = 7
        self.model = "fake-claude-context"
        self.calls: list[dict[str, object]] = []

    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        self.calls.append(payload)
        return PageSelectionResult(
            pages_used=[
                "index.md",
                "domoic-acid-scallops.md",
                "contaminants-foodex2.md",
                "domain-specific-validation.md",
            ],
            tool_trace=[
                {"page_name": "domoic-acid-scallops.md", "order": 1, "chars": 100, "synthetic": False},
                {"page_name": "contaminants-foodex2.md", "order": 2, "chars": 100, "synthetic": False},
                {
                    "page_name": "domain-specific-validation.md",
                    "order": 3,
                    "chars": 100,
                    "synthetic": False,
                },
            ],
            token_summary={
                "model": self.model,
                "calls": 1,
                "input_tokens": 80,
                "output_tokens": 20,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 100,
                "per_call": [],
            },
            timing_summary={"calls": 1, "llm_time_ms": 120, "per_call": []},
        )


def setup_function() -> None:
    app_module.librarian_runner = FakeLibrarian()
    app_module.selector_runner = FakeSelector()
    app_module.ask_selector_runner = FakeSelector()
    app_module.solver_runner = FakeSolver()
    app_module.answerer_runner = FakeAnswerer()


def test_get_selector_runner_default_scopes_never_cross_contaminate(monkeypatch) -> None:
    """The coding and ask default singletons must be distinct, scope-locked instances.

    /wiki/context-pack and /wiki/ask both call get_selector_runner() with no
    per-request model/effort override in the common case, so they share the
    "construct once, fall back to a module global" code path. This test
    guards against a regression where that path collapses back to a single
    shared instance (the pre-fix bug) by asserting the two scopes resolve to
    different objects, each locked to its own catalog_scope.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    app_module.selector_runner = None
    app_module.ask_selector_runner = None
    try:
        coding_runner = app_module.get_selector_runner(scope="coding")
        ask_runner = app_module.get_selector_runner(scope="ask")

        assert coding_runner is not ask_runner
        assert coding_runner.catalog_scope == "coding"
        assert ask_runner.catalog_scope == "ask"

        # Repeated calls with the same scope return the same cached instance,
        # and never adopt the other scope's catalog_scope.
        assert app_module.get_selector_runner(scope="coding") is coding_runner
        assert app_module.get_selector_runner(scope="ask") is ask_runner
        assert coding_runner.catalog_scope == "coding"
        assert ask_runner.catalog_scope == "ask"
    finally:
        app_module.selector_runner = None
        app_module.ask_selector_runner = None


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
    assert "README.md" in names
    assert "PROJECT_CONTEXT.md" in names
    assert "INGEST_WORKFLOW.md" in names
    assert "MAINTENANCE_WORKFLOW.md" in names
    assert "SCHEMA.md" in names
    assert "RUNTIME_RULES.md" in names
    assert "pesticides-foodex2.md" in names
    assert "contaminants-foodex2.md" in names
    assert "domoic-acid-scallops.md" in names
    assert "vmpr-foodex2.md" in names
    assert "additives-flavourings-foodex2.md" in names
    pages_by_name = {page["page_name"]: page for page in payload["pages"]}
    assert pages_by_name["MAINTENANCE_WORKFLOW.md"]["category"] == "orientation"
    assert pages_by_name["domoic-acid-scallops.md"]["category"] == "domain_overlay"


def test_get_unknown_page_returns_404() -> None:
    response = request("GET", "/wiki/pages/not-a-real-page.md")
    assert response.status_code == 404


def test_get_project_context_page_returns_200() -> None:
    response = request("GET", "/wiki/pages/PROJECT_CONTEXT.md")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_name"] == "PROJECT_CONTEXT.md"
    assert payload["title"] == "Project Context"
    assert "What We Are Building" in payload["content"]


def test_get_knowledge_architecture_page_returns_200() -> None:
    response = request("GET", "/wiki/pages/KNOWLEDGE_ARCHITECTURE.md")
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_name"] == "KNOWLEDGE_ARCHITECTURE.md"
    assert payload["title"] == "Knowledge Architecture"
    assert "Long-source workspace" in payload["content"]


def test_graph_view_route_returns_html() -> None:
    response = request("GET", "/wiki/graph-view")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "FoodEx2 Wiki Graph" in response.text
    assert "/wiki/graph/compact" in response.text


def test_wiki_viewer_builds_navigation_from_page_catalog() -> None:
    response = request("GET", "/wiki/view")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "normalizePageList(data.pages || [])" in response.text
    assert "/wiki/search?q=" in response.text
    assert "const sections = {" not in response.text


def test_wiki_search_finds_facet_text_without_llm() -> None:
    response = request("GET", "/wiki/search", params={"q": "fortification facet (F09)"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["terms"] == ["fortification", "facet", "F09"]
    assert payload["result_count"] >= 1
    first = payload["results"][0]
    assert first["page_name"] == "facet-coding-rules.md"
    assert first["category"] == "guidance"
    assert set(first["matches"]) == {"fortification", "facet", "F09"}
    assert any("Fortification component" in snippet for snippet in first["snippets"])


def test_wiki_search_returns_no_results_for_invented_phrase() -> None:
    response = request(
        "GET",
        "/wiki/search",
        params={"q": '"Add only when the descriptor is explicitly present or mandated by reporting context."'},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["result_count"] == 0
    assert payload["results"] == []


def test_wiki_rag_status_reports_deterministic_index_drift(monkeypatch) -> None:
    def fake_get_wiki_rag_status(**kwargs: object) -> dict[str, object]:
        return {
            "ok": False,
            "collection": kwargs["collection"] or "foodex2_wiki_markdown_v1",
            "qdrant_url": kwargs["qdrant_url"] or "http://127.0.0.1:6333",
            "embedding_provider": "voyage",
            "embedding_model": kwargs["embedding_model"] or "voyage-context-3",
            "embedding_dimension": kwargs["embedding_dimension"] or 1024,
            "chunking": {
                "max_chars": kwargs["max_chars"],
                "categories": ["guidance", "runtime"],
            },
            "expected": {
                "page_count": 2,
                "chunk_count": 4,
                "pages": ["RUNTIME_RULES.md", "base-term-selection.md"],
            },
            "indexed": {
                "collection_exists": True,
                "points_count": 3,
                "chunk_count": 3,
                "page_count": 2,
                "pages": ["RUNTIME_RULES.md", "old-page.md"],
                "payloadless_points": 0,
                "duplicate_chunk_ids": [],
            },
            "drift": {
                "missing_pages": ["base-term-selection.md"],
                "stale_pages": ["RUNTIME_RULES.md"],
                "orphaned_pages": ["old-page.md"],
                "missing_chunk_ids": ["base-term-selection.md#000-00-base-term-selection-rules"],
                "stale_chunk_ids": ["RUNTIME_RULES.md#000-00-runtime-rules"],
                "orphaned_chunk_ids": ["old-page.md#000-00-old-page"],
                "embedding_model_mismatch_chunk_ids": [],
                "embedding_dimension_mismatch_chunk_ids": [],
            },
            "errors": [],
        }

    monkeypatch.setattr(app_module, "get_wiki_rag_status", fake_get_wiki_rag_status)

    response = request("GET", "/wiki/rag/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is False
    assert payload["collection"] == "foodex2_wiki_markdown_v1"
    assert payload["drift"]["missing_pages"] == ["base-term-selection.md"]
    assert payload["drift"]["orphaned_pages"] == ["old-page.md"]


def test_wiki_graph_exposes_index_hub_edges() -> None:
    response = request("GET", "/wiki/graph")
    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]["page_count"] >= 30
    assert payload["summary"]["edge_count"] > 0
    assert any(node["page_name"] == "index.md" for node in payload["nodes"])
    assert any(
        edge["source"] == "index.md"
        and edge["target"] == "SCHEMA.md"
        and edge["type"] == "index_reference"
        for edge in payload["edges"]
    )


def test_compact_wiki_graph_is_frontend_friendly() -> None:
    response = request("GET", "/wiki/graph/compact")
    assert response.status_code == 200
    payload = response.json()

    schema_node = next(node for node in payload["nodes"] if node["id"] == "SCHEMA.md")
    assert schema_node["label"] == "Wiki Schema"
    assert schema_node["category"] == "orientation"
    assert schema_node["total_links"] == schema_node["incoming_count"] + schema_node["outgoing_count"]
    architecture_node = next(node for node in payload["nodes"] if node["id"] == "KNOWLEDGE_ARCHITECTURE.md")
    assert architecture_node["category"] == "orientation"
    vmpr_node = next(node for node in payload["nodes"] if node["id"] == "vmpr-legislative-mapping.md")
    assert vmpr_node["category"] == "domain_overlay"
    pesticide_node = next(node for node in payload["nodes"] if node["id"] == "pesticides-foodex2.md")
    assert pesticide_node["category"] == "domain_overlay"
    domoic_node = next(node for node in payload["nodes"] if node["id"] == "domoic-acid-scallops.md")
    assert domoic_node["category"] == "domain_overlay"
    assert any(
        edge["source"] == "index.md"
        and edge["target"] == "MAINTENANCE_WORKFLOW.md"
        and edge["type"] == "index_reference"
        for edge in payload["edges"]
    )
    assert any(
        edge["source"] == "index.md"
        and edge["target"] == "pesticides-foodex2.md"
        and edge["type"] == "index_reference"
        for edge in payload["edges"]
    )


def test_page_backlinks_returns_incoming_relationships() -> None:
    response = request("GET", "/wiki/pages/SCHEMA.md/backlinks")
    assert response.status_code == 200
    payload = response.json()

    assert payload["page_name"] == "SCHEMA.md"
    assert payload["backlink_count"] >= 1
    assert any(
        entry["source"] == "index.md" and entry["type"] == "index_reference"
        for entry in payload["backlinks"]
    )
    assert any(entry["source"] == "README.md" for entry in payload["backlinks"])


def test_ask_returns_answer_with_citations_and_trace() -> None:
    response = request(
        "POST",
        "/wiki/ask",
        json={
            "question": "How should I think about coding fresh cheese made from milk?",
            "max_pages": 7,
            "use_graph_expansion": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert "classifying the item as a derivative" in payload["answer"]
    assert payload["citations"] == ["base-term-selection.md", "implicit-vs-explicit-facets.md"]
    assert payload["pages_used"] == [
        "index.md",
        "base-term-selection.md",
        "ingredient-facets.md",
        "packaging-facets.md",
        "term-type-facet-constraints.md",
        "implicit-vs-explicit-facets.md",
    ]
    assert payload["trace"]["selection_method"] == "service-owned llm page selector + answerer"
    assert payload["trace"]["retrieval"]["model"] == "fake-claude-context"
    assert payload["trace"]["answerer"]["model"] == "fake-claude-answerer"
    assert payload["trace"]["total"]["total_llm_calls"] == 2
    assert payload["trace"]["total"]["total_tracked_tokens"] == 405
    assert app_module.answerer_runner.calls[0]["question"] == (
        "How should I think about coding fresh cheese made from milk?"
    )
    first_page = app_module.answerer_runner.calls[0]["pages"][0]
    assert first_page["page_name"] == "index.md"
    assert "content" in first_page


def test_ask_select_pages_runs_only_selector_and_records_usage() -> None:
    response = request(
        "POST",
        "/wiki/ask/select-pages",
        json={
            "question": "What changed in the 2024 maintenance release?",
            "max_pages": 6,
            "include_page_content": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pages_used"] == [
        "index.md",
        "base-term-selection.md",
        "ingredient-facets.md",
        "packaging-facets.md",
        "term-type-facet-constraints.md",
        "implicit-vs-explicit-facets.md",
    ]
    assert payload["trace"]["selection_method"] == "service-owned llm page selector"
    assert payload["trace"]["total"] == {
        "request_wall_time_ms": payload["trace"]["total"]["request_wall_time_ms"],
        "total_llm_calls": 1,
        "total_tracked_tokens": 115,
    }
    assert app_module.answerer_runner.calls == []
    assert all(page["content"] is None for page in payload["pages"])


def test_ask_rag_uses_qdrant_context_and_answerer(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_retrieve_qdrant_ask_context(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "answerer_pages": [
                {
                    "page_name": "base-term-selection.md",
                    "content": "Food type first, then select the base term.",
                },
                {
                    "page_name": "implicit-vs-explicit-facets.md",
                    "content": "Do not duplicate implicit facets.",
                },
            ],
            "page_summaries": [
                {
                    "page_name": "base-term-selection.md",
                    "title": "Base Term Selection Rules",
                    "summary": "Choose food type and base term.",
                    "category": "rules",
                    "sources": [],
                    "related": [],
                    "content": "Food type first, then select the base term.",
                },
                {
                    "page_name": "implicit-vs-explicit-facets.md",
                    "title": "Implicit vs Explicit Facets",
                    "summary": "Account for implicit facets.",
                    "category": "rules",
                    "sources": [],
                    "related": [],
                    "content": "Do not duplicate implicit facets.",
                },
            ],
            "pages_used": ["base-term-selection.md", "implicit-vs-explicit-facets.md"],
            "embedding": {
                "provider": "voyage",
                "model": "voyage-context-3",
                "dimension": 1024,
                "elapsed_ms": 20,
                "usage": {"total_tokens": 12},
                "tracked_tokens": 12,
            },
            "retrieval": {
                "provider": "qdrant",
                "retrieval_mode": "wiki",
                "collection": "foodex2_wiki_markdown_v1",
                "qdrant_url": "http://127.0.0.1:6333",
                "elapsed_ms": 5,
                "limit": 3,
                "result_count": 2,
                "results": [
                    {"score": 0.91, "page_name": "base-term-selection.md"},
                    {"score": 0.88, "page_name": "implicit-vs-explicit-facets.md"},
                ],
            },
        }

    monkeypatch.setattr(app_module, "retrieve_qdrant_ask_context", fake_retrieve_qdrant_ask_context)

    response = request(
        "POST",
        "/wiki/ask-rag",
        json={
            "question": "What should I think about when coding dried chili?",
            "retrieval_mode": "wiki",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["selection_method"] == "qdrant wiki retrieval + answerer"
    assert payload["trace"]["retrieval"]["collection"] == "foodex2_wiki_markdown_v1"
    assert payload["trace"]["embedding"]["tracked_tokens"] == 12
    assert payload["trace"]["total"]["total_llm_calls"] == 1
    assert payload["trace"]["total"]["total_embedding_calls"] == 1
    assert payload["trace"]["total"]["total_tracked_tokens"] == 302
    assert payload["citations"] == ["base-term-selection.md", "implicit-vs-explicit-facets.md"]
    assert payload["pages"][0]["content"] is None
    assert calls[0]["retrieval_mode"] == "wiki"
    assert calls[0]["limit"] == 3
    assert app_module.answerer_runner.calls[0]["pages"][0]["page_name"] == "base-term-selection.md"


def test_ask_rag_can_return_source_rag_with_page_content(monkeypatch) -> None:
    class SourceAnswerer(FakeAnswerer):
        def run(self, *, question: str, pages: list[dict[str, object]]) -> AnswerResult:
            self.calls.append({"question": question, "pages": pages})
            return AnswerResult(
                answer="Use the raw source chunk as source evidence, then classify with catalogue data.",
                citations=["guidance.pdf"],
                token_summary={
                    "model": self.model,
                    "calls": 1,
                    "input_tokens": 100,
                    "output_tokens": 40,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "total_tracked_tokens": 140,
                    "per_call": [],
                },
                timing_summary={"calls": 1, "llm_time_ms": 300, "per_call": []},
            )

    def fake_retrieve_qdrant_ask_context(**kwargs: object) -> dict[str, object]:
        return {
            "answerer_pages": [
                {"page_name": "guidance.pdf", "content": "Source file: guidance.pdf\nLocation: page 4"}
            ],
            "page_summaries": [
                {
                    "page_name": "guidance.pdf",
                    "title": "guidance.pdf :: page 4",
                    "summary": "foodex2_docs/guidance.pdf",
                    "category": "source_document",
                    "sources": ["foodex2_docs/guidance.pdf"],
                    "related": [],
                    "content": "Source file: guidance.pdf\nLocation: page 4",
                }
            ],
            "pages_used": ["guidance.pdf"],
            "embedding": {
                "provider": "voyage",
                "model": "voyage-context-3",
                "dimension": 1024,
                "elapsed_ms": 25,
                "usage": {},
                "tracked_tokens": None,
            },
            "retrieval": {
                "provider": "qdrant",
                "retrieval_mode": "source",
                "collection": "foodex2_source_docs_v1",
                "qdrant_url": "http://127.0.0.1:6333",
                "elapsed_ms": 6,
                "limit": 2,
                "result_count": 1,
                "results": [{"score": 0.87, "source_file": "guidance.pdf", "location": "page 4"}],
            },
        }

    app_module.answerer_runner = SourceAnswerer()
    monkeypatch.setattr(app_module, "retrieve_qdrant_ask_context", fake_retrieve_qdrant_ask_context)

    response = request(
        "POST",
        "/wiki/ask-rag",
        json={
            "question": "What should I think about when reporting sheep urine?",
            "retrieval_mode": "source",
            "limit": 2,
            "include_page_content": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["selection_method"] == "qdrant source retrieval + answerer"
    assert payload["trace"]["retrieval"]["collection"] == "foodex2_source_docs_v1"
    assert payload["trace"]["total"]["total_tracked_tokens"] == 140
    assert payload["citations"] == ["guidance.pdf"]
    assert "Source file" in payload["pages"][0]["content"]


def test_ask_accepts_per_request_model_overrides(monkeypatch) -> None:
    created: dict[str, object] = {}

    class OverrideSelector(FakeSelector):
        def __init__(
            self, *, store: object, model: str, max_pages: int, catalog_scope: str = "coding"
        ) -> None:
            super().__init__()
            self.model = model
            self.max_pages = max_pages
            self.catalog_scope = catalog_scope
            created["selector"] = self

    class OverrideAnswerer(FakeAnswerer):
        def __init__(self, *, model: str) -> None:
            super().__init__()
            self.model = model
            created["answerer"] = self

    monkeypatch.setattr(app_module, "AnthropicWikiPageSelector", OverrideSelector)
    monkeypatch.setattr(app_module, "AnthropicFoodEx2Answerer", OverrideAnswerer)

    response = request(
        "POST",
        "/wiki/ask",
        json={
            "question": "How should I think about coding fresh cheese made from milk?",
            "selector_model": " selector-test-model ",
            "answerer_model": " answerer-test-model ",
            "max_pages": 5,
            "use_graph_expansion": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["retrieval"]["model"] == "selector-test-model"
    assert payload["trace"]["answerer"]["model"] == "answerer-test-model"
    assert created["selector"].max_pages == 5
    assert created["selector"].catalog_scope == "ask"


def test_ask_routes_non_anthropic_model_overrides(monkeypatch) -> None:
    created: dict[str, object] = {}

    class JsonSelector(FakeSelector):
        def __init__(
            self, *, store: object, model: str, max_pages: int, catalog_scope: str = "coding"
        ) -> None:
            super().__init__()
            self.model = model
            self.max_pages = max_pages
            self.catalog_scope = catalog_scope
            created["selector"] = self

    class JsonAnswerer(FakeAnswerer):
        def __init__(self, *, model: str) -> None:
            super().__init__()
            self.model = model
            created["answerer"] = self

    monkeypatch.setattr(app_module, "JsonWikiPageSelector", JsonSelector)
    monkeypatch.setattr(app_module, "JsonFoodEx2Answerer", JsonAnswerer)

    response = request(
        "POST",
        "/wiki/ask",
        json={
            "question": "How should I think about coding fresh cheese made from milk?",
            "selector_model": "gpt-5.4-mini",
            "answerer_model": "gemini-3.5-flash",
            "use_graph_expansion": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["retrieval"]["model"] == "gpt-5.4-mini"
    assert payload["trace"]["answerer"]["model"] == "gemini-3.5-flash"
    assert created["selector"].model == "gpt-5.4-mini"
    assert created["answerer"].model == "gemini-3.5-flash"
    assert created["selector"].catalog_scope == "ask"


def test_ask_routes_lmstudio_model_overrides_through_messages_client(monkeypatch) -> None:
    created: dict[str, object] = {}

    class OverrideSelector(FakeSelector):
        def __init__(
            self, *, store: object, model: str, max_pages: int, catalog_scope: str = "coding"
        ) -> None:
            super().__init__()
            self.model = model
            self.max_pages = max_pages
            self.catalog_scope = catalog_scope
            created["selector"] = self

    class OverrideAnswerer(FakeAnswerer):
        def __init__(self, *, model: str) -> None:
            super().__init__()
            self.model = model
            created["answerer"] = self

    monkeypatch.setattr(app_module, "AnthropicWikiPageSelector", OverrideSelector)
    monkeypatch.setattr(app_module, "AnthropicFoodEx2Answerer", OverrideAnswerer)

    response = request(
        "POST",
        "/wiki/ask",
        json={
            "question": "What should I think about when reporting sheep urine?",
            "selector_model": "lmstudio:qwen-local",
            "answerer_model": "lmstudio:qwen-local",
            "use_graph_expansion": False,
        },
    )

    assert response.status_code == 200
    assert created["selector"].model == "lmstudio:qwen-local"
    assert created["answerer"].model == "lmstudio:qwen-local"


def test_ask_passes_reasoning_effort_to_lmstudio_overrides(monkeypatch) -> None:
    created: dict[str, object] = {}

    class OverrideSelector(FakeSelector):
        def __init__(
            self,
            *,
            store: object,
            model: str,
            max_pages: int,
            reasoning_effort: str | None = None,
            catalog_scope: str = "coding",
        ) -> None:
            super().__init__()
            self.model = model
            self.max_pages = max_pages
            self.reasoning_effort = reasoning_effort
            self.catalog_scope = catalog_scope
            created["selector"] = self

    class OverrideAnswerer(FakeAnswerer):
        def __init__(
            self,
            *,
            model: str,
            reasoning_effort: str | None = None,
        ) -> None:
            super().__init__()
            self.model = model
            self.reasoning_effort = reasoning_effort
            created["answerer"] = self

    monkeypatch.setattr(app_module, "AnthropicWikiPageSelector", OverrideSelector)
    monkeypatch.setattr(app_module, "AnthropicFoodEx2Answerer", OverrideAnswerer)

    response = request(
        "POST",
        "/wiki/ask",
        json={
            "question": "What should I think about when reporting sheep urine?",
            "selector_model": "lmstudio:gpt-oss-120b",
            "answerer_model": "lmstudio:gpt-oss-120b",
            "selector_reasoning_effort": "high",
            "answerer_reasoning_effort": "high",
            "use_graph_expansion": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert created["selector"].reasoning_effort == "high"
    assert created["answerer"].reasoning_effort == "high"
    assert payload["trace"]["retrieval"]["reasoning_effort"] == "high"
    assert payload["trace"]["answerer"]["reasoning_effort"] == "high"
    assert created["selector"].catalog_scope == "ask"


def test_ask_requires_question() -> None:
    response = request("POST", "/wiki/ask", json={"question": ""})
    assert response.status_code == 422


def test_ask_returns_503_for_bad_answerer_output() -> None:
    app_module.answerer_runner = FakeBadAnswerer()

    response = request(
        "POST",
        "/wiki/ask",
        json={"question": "How should I think about coding fresh cheese?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not extract JSON object from answerer response"


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
                {
                    "code": "A044C",
                    "name": "Tomato-containing cooked sauces",
                    "termType": "s",
                    "scopeNote": "noisy legacy field that should be reduced",
                    "implicitFacets": [{"facetType": "F04", "facetCode": "A0DMX", "facetMeaning": "Tomatoes"}],
                    "monitoringFlags": {"reportFlag": True},
                },
                {
                    "code": "A07NN",
                    "name": "Jar",
                    "termType": "f",
                    "additionalMetadata": {"score": 0.91},
                },
                {"code": "A07PF", "name": "Glass", "termType": "f"},
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["guiding_principles"]) >= 4
    assert payload["policy_contract"]["policy_version"] == "2026-06-07-v0.6"
    assert payload["policy_contract"]["constitution"][0]["id"] == "C01"
    assert payload["policy_contract"]["anti_patterns"][0]["id"] == "AP-001"
    assert "business-rules.md BR19" in payload["policy_contract"]["binding_rules"][0]["derived_from"]
    assert payload["guiding_principles"][1].startswith("FoodEx2 is built top-down.")
    assert payload["pages_used"] == [
        "policy-contract.md",
        "index.md",
        "base-term-selection.md",
        "packaging-facets.md",
        "ingredient-facets.md",
    ]
    assert payload["trace"]["selection_method"] == "service-owned llm librarian"
    assert payload["trace"]["model"] == "fake-claude"
    assert payload["trace"]["candidate_input_mode"] == "candidates->candidates_trimmed"
    assert payload["trace"]["token_summary"]["total_tracked_tokens"] == 200
    assert payload["trace"]["timing_summary"]["llm_time_ms"] == 1420
    assert payload["trace"]["timing_summary"]["librarian_wall_time_ms"] == 1600
    assert payload["trace"]["timing_summary"]["request_wall_time_ms"] >= 0
    assert payload["query_classification"]["food_type"] == "composite"
    assert payload["pages"][0]["page_name"] == "policy-contract.md"
    assert payload["pages"][3]["page_name"] == "packaging-facets.md"
    assert app_module.librarian_runner.calls[0]["candidates"] == [
        {
            "code": "A044C",
            "name": "Tomato-containing cooked sauces",
            "termType": "s",
            "coverageText": "noisy legacy field that should be reduced",
            "implicitFacets": [{"facetType": "F04", "facetCode": "A0DMX", "facetMeaning": "Tomatoes"}],
        },
        {"code": "A07NN", "name": "Jar", "termType": "f"},
        {"code": "A07PF", "name": "Glass", "termType": "f"},
    ]


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
                {
                    "code": "A044C",
                    "name": "Tomato-containing cooked sauces",
                    "termType": "s",
                    "scopeNote": "legacy field should not reach selector",
                    "implicitFacets": [{"facetType": "F04", "facetCode": "A0DMX"}],
                },
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["guiding_principles"]) >= 4
    assert payload["policy_contract"]["policy_version"] == "2026-06-07-v0.6"
    assert payload["policy_contract"]["constitution"][0]["id"] == "C01"
    assert payload["guiding_principles"][2].startswith("FoodEx2 prefers modular description")
    assert payload["pages_used"] == [
        "RUNTIME_RULES.md",
        "index.md",
        "base-term-selection.md",
        "ingredient-facets.md",
        "packaging-facets.md",
        "term-type-facet-constraints.md",
        "implicit-vs-explicit-facets.md",
    ]
    assert "policy_pack" not in payload
    assert "query_classification" not in payload
    assert payload["trace"]["selection_method"] == "service-owned llm page selector"
    assert payload["trace"]["candidate_input_mode"] == "candidates->candidate_hints"
    assert payload["trace"]["index_used"] is True
    assert payload["trace"]["token_summary"]["calls"] == 1
    assert payload["trace"]["token_summary"]["total_tracked_tokens"] == 115
    assert payload["trace"]["timing_summary"]["llm_time_ms"] == 480
    assert payload["trace"]["model"] == "fake-claude-context"
    assert payload["trace"]["timing_summary"]["request_wall_time_ms"] >= 0
    assert payload["pages"][0]["page_name"] == "RUNTIME_RULES.md"
    assert payload["trace"]["tool_trace"][0]["page_name"] == "base-term-selection.md"
    assert payload["trace"]["prompt_projection"]["content_mode"] == "classification_prompt"
    pages_by_name = {page["page_name"]: page for page in payload["pages"]}
    assert pages_by_name["index.md"]["content"] is None
    runtime_content = pages_by_name["RUNTIME_RULES.md"]["content"]
    assert runtime_content is not None
    assert not runtime_content.startswith("# Runtime Rules")
    assert "compact prompt-facing rules file" not in runtime_content
    assert "Use it as the always-on runtime layer" not in runtime_content
    assert "## Core Decision Order" in runtime_content
    assert "Treat reporting-domain overlays as opt-in" in runtime_content
    assert "Treat returned wiki pages as coding knowledge" in runtime_content
    assert "candidate list is retrieval evidence" in runtime_content
    assert "Do not invent FoodEx2 codes from memory" in runtime_content
    assert "mark the candidate set incomplete" in runtime_content
    assert "## Supporting Pages By Signal" not in runtime_content
    assert "Worked Examples" not in runtime_content
    base_content = pages_by_name["base-term-selection.md"]["content"]
    assert base_content is not None
    assert not base_content.startswith("# Base Term Selection")
    assert "## Start With Food Type" in base_content
    assert "## Worked Examples" not in base_content
    assert "kangaroo fresh fat tissue" not in base_content
    assert "## Relevant Policy" not in base_content
    assert "## Relevant Business Rules" not in base_content
    assert "[[" not in base_content
    assert app_module.selector_runner.calls[0]["candidates"] == [
        {
            "code": "A044C",
            "name": "Tomato-containing cooked sauces",
            "termType": "s",
        }
    ]


def test_context_pack_can_return_domoic_acid_scallop_overlay() -> None:
    app_module.selector_runner = FakeDomoicAcidScallopSelector()

    response = request(
        "POST",
        "/wiki/context-pack",
        json={
            "search_term": "domoic acid in Pecten maximus hepatopancreas",
            "deconstructed_query": {
                "analyte": "domoic acid",
                "matrix": "scallop",
                "species": "Pecten maximus",
                "part": "hepatopancreas",
            },
            "candidate_hints": [
                {"code": "A16FR", "name": "Scallop edible offal", "termType": "r"},
            ],
            "context": {"reporting_domain": "contaminants"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pages_used"][0] == "RUNTIME_RULES.md"
    assert len(payload["pages_used"]) <= 7
    assert "domoic-acid-scallops.md" in payload["pages_used"]
    pages_by_name = {page["page_name"]: page for page in payload["pages"]}
    content = pages_by_name["domoic-acid-scallops.md"]["content"]
    assert content is not None
    assert "## Reporting Rule" in content
    assert "`A16FR#F01.A055P$F20.A18FH`" in content
    assert "Pecten maximus, Hepatopancreas" in content
    assert "origFishAreaCode" in content
    assert app_module.selector_runner.calls[0]["context"] == {"reporting_domain": "contaminants"}


class FakeLeakySelector(FakeSelector):
    def run(self, payload: dict[str, object]) -> PageSelectionResult:
        result = super().run(payload)
        return PageSelectionResult(
            pages_used=["index.md", "base-term-selection.md", "ingredient-facets.md", "maintenance-2024.md"],
            tool_trace=result.tool_trace,
            token_summary=result.token_summary,
            timing_summary=result.timing_summary,
        )


def test_context_pack_backfills_missing_roles_and_drops_leaks() -> None:
    app_module.selector_runner = FakeLeakySelector()
    response = request(
        "POST",
        "/wiki/context-pack",
        json={"search_term": "test skeleton enforcement"},
    )
    assert response.status_code == 200
    payload = response.json()
    pages_used = payload["pages_used"]
    assert pages_used[0] == "RUNTIME_RULES.md"
    assert "maintenance-2024.md" not in pages_used
    assert "term-type-facet-constraints.md" in pages_used
    enforcement = payload["trace"]["skeleton_enforcement"]
    assert enforcement["backfilled"] == [
        {"role": "validation", "page": "term-type-facet-constraints.md"}
    ]
    assert enforcement["dropped"] == ["maintenance-2024.md"]
    assert enforcement["selector_covered_roles"] == ["base_term", "facet"]
    page_names = [page["page_name"] for page in payload["pages"]]
    assert "term-type-facet-constraints.md" in page_names
    assert "maintenance-2024.md" not in page_names


def test_context_pack_trace_reports_no_backfill_when_roles_covered() -> None:
    response = request(
        "POST",
        "/wiki/context-pack",
        json={"search_term": "test skeleton no-op"},
    )
    assert response.status_code == 200
    enforcement = response.json()["trace"]["skeleton_enforcement"]
    assert enforcement["backfilled"] == []
    assert enforcement["dropped"] == []
    assert enforcement["trimmed"] == []


def test_context_pack_max_pages_is_a_strict_final_response_cap() -> None:
    response = request(
        "POST",
        "/wiki/context-pack",
        json={"search_term": "strict cap", "max_pages": 4},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["pages_used"]) == 4
    assert payload["pages_used"][0] == "RUNTIME_RULES.md"
    assert "base-term-selection.md" in payload["pages_used"]
    assert "ingredient-facets.md" in payload["pages_used"]
    assert "term-type-facet-constraints.md" in payload["pages_used"]
    assert payload["trace"]["skeleton_enforcement"]["trimmed"] == [
        "index.md",
        "implicit-vs-explicit-facets.md",
        "packaging-facets.md",
    ]


def test_policy_pack_accepts_legacy_scope_note_but_normalizes_to_coverage_text() -> None:
    response = request(
        "POST",
        "/wiki/policy-pack",
        json={
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {},
            "candidates_trimmed": [
                {
                    "code": "A044C",
                    "name": "Tomato-containing cooked sauces",
                    "termType": "s",
                    "scopeNote": "legacy candidate scope note",
                }
            ],
            "context": {},
        },
    )
    assert response.status_code == 200
    assert app_module.librarian_runner.calls[0]["candidates"] == [
        {
            "code": "A044C",
            "name": "Tomato-containing cooked sauces",
            "termType": "s",
            "coverageText": "legacy candidate scope note",
            "implicitFacets": [],
        }
    ]


def test_policy_pack_page_content_is_model_cleaned() -> None:
    response = request(
        "POST",
        "/wiki/policy-pack",
        json={
            "search_term": "Tomato basil and garlic sauce in a glass jar",
            "deconstructed_query": {},
            "candidates": [{"code": "A044C", "name": "Tomato-containing cooked sauces", "termType": "s"}],
            "context": {},
            "include_page_content": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    content = payload["pages"][0]["content"]
    assert content is not None
    assert "<!-- Source:" not in content
    assert not content.startswith("---")


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
    assert payload["policy_contract"]["policy_version"] == "2026-06-07-v0.6"
    assert payload["solution"]["constructedCode"] == "A044C#F04.A00VV$F04.A00GZ$F18.A07NN$F19.A07PF"
    assert payload["solution"]["validationCheck"]["passes"] is True
    assert payload["solution"]["confidence"] == 5
    assert payload["trace"]["selection_method"] == "service-owned llm librarian + solver"
    assert payload["trace"]["retrieval"]["model"] == "fake-claude"
    assert payload["trace"]["solver"]["model"] == "fake-claude-solver"
    assert payload["trace"]["total"]["total_llm_calls"] == 3
    assert payload["trace"]["total"]["total_tracked_tokens"] == 620
    assert len(payload["guiding_principles"]) >= 4
    assert app_module.solver_runner.calls[0]["policy_contract"]["constitution"][0]["id"] == "C01"
    assert app_module.solver_runner.calls[0]["policy_contract"]["binding_rules"][0]["id"] == "R-DERIV-001"


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


def test_solve_returns_503_for_malformed_solver_output() -> None:
    app_module.solver_runner = FakeBadSolver()

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
            ],
            "context": {},
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not extract JSON object from solver response"


def test_openapi_exposes_endpoint_specific_candidate_contracts() -> None:
    response = request("GET", "/openapi.json")
    assert response.status_code == 200
    payload = response.json()

    context_props = payload["components"]["schemas"]["ContextPackRequest"]["properties"]
    policy_props = payload["components"]["schemas"]["PolicyPackRequest"]["properties"]
    solve_props = payload["components"]["schemas"]["SolveRequest"]["properties"]
    trimmed_props = payload["components"]["schemas"]["CandidateTrimmed"]["properties"]
    solve_candidate_props = payload["components"]["schemas"]["SolveCandidate"]["properties"]

    assert "candidate_hints" in context_props
    assert "candidates_trimmed" not in context_props
    assert "candidates_trimmed" in policy_props
    assert "candidate_hints" not in policy_props
    assert "candidates" in solve_props
    assert "coverageText" in trimmed_props
    assert "scopeNote" not in trimmed_props
    assert "coverageText" in solve_candidate_props
    assert "scopeNote" not in solve_candidate_props
    assert "policy_contract" in payload["components"]["schemas"]["ContextPackResponse"]["properties"]
    assert "policy_contract" in payload["components"]["schemas"]["PolicyPackResponse"]["properties"]
    assert "policy_contract" in payload["components"]["schemas"]["SolveResponse"]["properties"]
    assert "/wiki/ask" in payload["paths"]
    assert "/wiki/ask/select-pages" in payload["paths"]
    assert "/wiki/ask-rag" in payload["paths"]
    assert "/wiki/search" in payload["paths"]
    assert "/wiki/graph" in payload["paths"]
    assert "/wiki/graph/compact" in payload["paths"]
    assert "/wiki/pages/{page_name}/backlinks" in payload["paths"]

    context_description = payload["paths"]["/wiki/context-pack"]["post"]["description"]
    policy_description = payload["paths"]["/wiki/policy-pack"]["post"]["description"]
    solve_description = payload["paths"]["/wiki/solve"]["post"]["description"]

    assert "`candidate_hints`" in context_description
    assert context_props["max_pages"]["default"] == 7
    assert context_props["max_pages"]["minimum"] == 4
    assert "choose and return prompt-ready context pages" in context_description
    assert "deterministically" not in context_description
    assert "`candidates_trimmed`" in policy_description
    assert "`coverageText`" in policy_description
    assert "`scopeNote`" not in policy_description
    assert "`candidates`" in solve_description


def test_policy_contract_is_loaded_from_markdown_source() -> None:
    contract = build_policy_contract()
    assert contract["policy_version"] == "2026-06-07-v0.6"
    assert contract["constitution"][0]["id"] == "C01"
    assert contract["decision_procedure"][0]["name"] == "determine_food_type"
    assert contract["anti_patterns"][0]["id"] == "AP-001"
    assert contract["binding_rules"][0]["id"] == "R-DERIV-001"
    assert contract["binding_rules"][8]["id"] == "R-DESC-001"
    assert "business-rules.md BR19" in contract["constitution"][2]["derived_from"]
    assert "execution-layer" in contract["constitution"][4]["derived_from"]
    binding_rules_by_id = {rule["id"]: rule for rule in contract["binding_rules"]}
    assert binding_rules_by_id["R-PROC-001"]["should"].startswith(
        "keep at most one process per ordinal group"
    )
    assert "business-rules.md BR26" in binding_rules_by_id["R-PROC-001"]["derived_from"]
    assert "business-rules.md BR25" in binding_rules_by_id["R-CARD-001"]["derived_from"]
