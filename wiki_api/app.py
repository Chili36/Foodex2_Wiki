from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .librarian import (
    AnthropicFoodEx2Answerer,
    AnthropicFoodEx2Solver,
    AnthropicWikiLibrarian,
    AnthropicWikiPageSelector,
)
from .policy import build_policy_contract
from .wiki_store import WikiPage, WikiStore


_WIKI_LINK_RE = re.compile(r"\[\[([a-zA-Z0-9_\-]+)(?:\|[^\]]+)?\]\]")
REPO_ROOT = Path(__file__).resolve().parent.parent
store = WikiStore(REPO_ROOT)
librarian_runner: AnthropicWikiLibrarian | Any | None = None
selector_runner: Any | None = None
solver_runner: AnthropicFoodEx2Solver | Any | None = None
answerer_runner: AnthropicFoodEx2Answerer | Any | None = None
logger = logging.getLogger("wiki_api")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def get_librarian_runner() -> AnthropicWikiLibrarian | Any:
    global librarian_runner
    if librarian_runner is None:
        librarian_runner = AnthropicWikiLibrarian(store=store)
    return librarian_runner


def get_selector_runner() -> Any:
    global selector_runner
    if selector_runner is None:
        selector_runner = AnthropicWikiPageSelector(store=store)
    return selector_runner


def get_solver_runner() -> AnthropicFoodEx2Solver | Any:
    global solver_runner
    if solver_runner is None:
        solver_runner = AnthropicFoodEx2Solver()
    return solver_runner


def get_answerer_runner() -> AnthropicFoodEx2Answerer | Any:
    global answerer_runner
    if answerer_runner is None:
        answerer_runner = AnthropicFoodEx2Answerer()
    return answerer_runner


class CandidateHint(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = Field(description="FoodEx2 code.")
    name: str = Field(description="FoodEx2 display name.")
    termType: str = Field(description="FoodEx2 term type such as r, d, c, s, h, g, or f.")


class CandidateFacet(BaseModel):
    model_config = ConfigDict(extra="allow")

    facetType: str
    facetCode: str
    facetMeaning: str | None = None


class CandidateTrimmed(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = Field(description="FoodEx2 code.")
    name: str = Field(description="FoodEx2 display name.")
    termType: str = Field(description="FoodEx2 term type such as r, d, c, s, h, g, or f.")
    coverageText: str | None = Field(
        default=None,
        description="Optional candidate coverage text used for base-term and facet reasoning.",
    )
    implicitFacets: list[CandidateFacet] = Field(
        default_factory=list,
        description="Optional implicit facets already carried by the candidate term.",
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_scope_note(cls, data: Any) -> Any:
        if isinstance(data, dict):
            normalized = dict(data)
            legacy = normalized.pop("scopeNote", None)
            if normalized.get("coverageText") is None and legacy is not None:
                normalized["coverageText"] = legacy
            return normalized
        return data


class SolveCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = Field(description="FoodEx2 code.")
    name: str = Field(description="FoodEx2 display name.")
    termType: str = Field(description="FoodEx2 term type such as r, d, c, s, h, g, or f.")
    coverageText: str | None = Field(
        default=None,
        description="Optional candidate coverage text from retrieval.",
    )
    implicitFacets: list[CandidateFacet] = Field(
        default_factory=list,
        description="Optional implicit facets already carried by the candidate term.",
    )
    monitoringFlags: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional monitoring or regulatory flags from the search system.",
    )
    additionalMetadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional extra candidate metadata preserved for the solver.",
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_scope_note(cls, data: Any) -> Any:
        if isinstance(data, dict):
            normalized = dict(data)
            legacy = normalized.pop("scopeNote", None)
            if normalized.get("coverageText") is None and legacy is not None:
                normalized["coverageText"] = legacy
            return normalized
        return data


class CommonRequestFields(BaseModel):
    search_term: str
    deconstructed_query: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    max_pages: int = Field(default=6, ge=1, le=10)
    include_page_content: bool = True


class ContextPackRequest(CommonRequestFields):
    max_pages: int = Field(default=7, ge=1, le=10)
    candidate_hints: list[CandidateHint] = Field(
        default_factory=list,
        description=(
            "Preferred candidate input for /wiki/context-pack. Keep this minimal: "
            "code, name, and termType only."
        ),
    )
    candidates: list[SolveCandidate] = Field(
        default_factory=list,
        description=(
            "Legacy compatibility input. If provided, the service will internally reduce it to "
            "candidate hints before page selection."
        ),
        deprecated=True,
    )


class PolicyPackRequest(CommonRequestFields):
    candidates_trimmed: list[CandidateTrimmed] = Field(
        default_factory=list,
        description=(
            "Preferred candidate input for /wiki/policy-pack. Include only fields needed for "
            "reasoning: code, name, termType, optional coverageText, and optional implicitFacets."
        ),
    )
    candidates: list[SolveCandidate] = Field(
        default_factory=list,
        description=(
            "Legacy compatibility input. If provided, the service will internally reduce it to "
            "trimmed candidates before calling the LLM librarian."
        ),
        deprecated=True,
    )


class SolveRequest(CommonRequestFields):
    candidates: list[SolveCandidate] = Field(
        default_factory=list,
        description=(
            "Required full candidate universe for /wiki/solve. This endpoint keeps the richer "
            "candidate payload because it makes the final coding decision."
        ),
    )


class PageSummary(BaseModel):
    page_name: str
    title: str
    summary: str
    sources: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    content: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, description="The user's FoodEx2 coding question.")
    max_pages: int = Field(default=7, ge=1, le=10)
    include_page_content: bool = True
    use_graph_expansion: bool = Field(
        default=True,
        description=(
            "If true, add summary-only context for curated related pages adjacent to the "
            "selected pages."
        ),
    )


class AskResponse(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    pages_used: list[str] = Field(default_factory=list)
    pages: list[PageSummary] = Field(default_factory=list)
    trace: dict[str, Any]


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    section: str | None = None
    label: str | None = None


class GraphNode(BaseModel):
    page_name: str
    title: str
    summary: str
    incoming_count: int
    outgoing_count: int


class GraphHub(BaseModel):
    page_name: str
    title: str
    incoming_count: int
    outgoing_count: int
    total_links: int


class GraphSummary(BaseModel):
    page_count: int
    edge_count: int
    orphan_pages: list[str] = Field(default_factory=list)
    hub_pages: list[GraphHub] = Field(default_factory=list)


class WikiGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    summary: GraphSummary


class CompactGraphNode(BaseModel):
    id: str
    label: str
    category: str
    incoming_count: int
    outgoing_count: int
    total_links: int


class CompactGraphEdge(BaseModel):
    source: str
    target: str
    type: str


class CompactWikiGraphResponse(BaseModel):
    nodes: list[CompactGraphNode] = Field(default_factory=list)
    edges: list[CompactGraphEdge] = Field(default_factory=list)
    summary: GraphSummary


class BacklinkEntry(BaseModel):
    source: str
    source_title: str
    type: str
    section: str | None = None
    label: str | None = None


class BacklinksResponse(BaseModel):
    page_name: str
    title: str
    summary: str
    backlinks: list[BacklinkEntry] = Field(default_factory=list)
    backlink_count: int


class QueryClassification(BaseModel):
    food_type: str
    domain: str
    signals: list[str] = Field(default_factory=list)
    candidate_term_types: list[str] = Field(default_factory=list)


class CandidateFocus(BaseModel):
    promising_codes: list[str] = Field(default_factory=list)
    rejected_patterns: list[str] = Field(default_factory=list)


class PolicyPackBody(BaseModel):
    base_term_rules: list[str] = Field(default_factory=list)
    facet_rules: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)
    domain_rules: list[str] = Field(default_factory=list)
    construction_rules: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    wiki_gaps: list[str] = Field(default_factory=list)


class ConstitutionRule(BaseModel):
    id: str
    text: str
    priority: int
    derived_from: list[str] = Field(default_factory=list)


class DecisionProcedureStep(BaseModel):
    step: int
    name: str
    instruction: str
    derived_from: list[str] = Field(default_factory=list)


class BindingRule(BaseModel):
    id: str
    when: str
    must: str | None = None
    must_not: str | None = None
    may: str | None = None
    derived_from: list[str] = Field(default_factory=list)


class TieBreakRule(BaseModel):
    id: str
    when: str
    prefer: str
    derived_from: list[str] = Field(default_factory=list)


class AntiPattern(BaseModel):
    id: str
    pattern: str
    reject: bool = True
    derived_from: list[str] = Field(default_factory=list)


class PolicyContract(BaseModel):
    policy_version: str
    constitution: list[ConstitutionRule] = Field(default_factory=list)
    decision_procedure: list[DecisionProcedureStep] = Field(default_factory=list)
    binding_rules: list[BindingRule] = Field(default_factory=list)
    tie_break_rules: list[TieBreakRule] = Field(default_factory=list)
    anti_patterns: list[AntiPattern] = Field(default_factory=list)


class PolicyPackResponse(BaseModel):
    guiding_principles: list[str]
    policy_contract: PolicyContract
    pages_used: list[str]
    pages: list[PageSummary]
    query_classification: QueryClassification
    candidate_focus: CandidateFocus
    policy_pack: PolicyPackBody
    trace: dict[str, Any]


class ContextPackResponse(BaseModel):
    guiding_principles: list[str]
    policy_contract: PolicyContract
    pages_used: list[str]
    pages: list[PageSummary]
    trace: dict[str, Any]


class FacetSelection(BaseModel):
    facetType: str
    facetCode: str
    facetMeaning: str


class ValidationCheck(BaseModel):
    passes: bool
    rulesConsulted: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AlternativeCode(BaseModel):
    code: str
    name: str
    reason: str


class SolveResultBody(BaseModel):
    selectedCode: str
    selectedName: str
    selectedTermType: str
    constructedCode: str
    reasoning: str
    implicitFacets: list[FacetSelection] = Field(default_factory=list)
    suggestedExplicitFacets: list[FacetSelection] = Field(default_factory=list)
    validationCheck: ValidationCheck
    alternativeCodes: list[AlternativeCode] = Field(default_factory=list)
    confidence: int = Field(ge=1, le=5)
    regulatoryNotes: str = ""


class SolveResponse(BaseModel):
    guiding_principles: list[str]
    policy_contract: PolicyContract
    pages_used: list[str]
    pages: list[PageSummary]
    query_classification: QueryClassification
    candidate_focus: CandidateFocus
    policy_pack: PolicyPackBody
    solution: SolveResultBody
    trace: dict[str, Any]


def _plain_models(items: list[BaseModel | dict[str, Any]]) -> list[dict[str, Any]]:
    plain: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, BaseModel):
            plain.append(item.model_dump(exclude_none=True))
        else:
            plain.append(dict(item))
    return plain


def _to_candidate_hints(items: list[BaseModel | dict[str, Any]]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for item in _plain_models(items):
        hints.append(
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "termType": item.get("termType", ""),
            }
        )
    return hints


def _to_candidates_trimmed(items: list[BaseModel | dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for item in _plain_models(items):
        candidate: dict[str, Any] = {
            "code": item.get("code", ""),
            "name": item.get("name", ""),
            "termType": item.get("termType", ""),
        }
        coverage_text = item.get("coverageText") or item.get("scopeNote")
        if coverage_text:
            candidate["coverageText"] = coverage_text
        implicit_facets = item.get("implicitFacets") or []
        if implicit_facets:
            candidate["implicitFacets"] = implicit_facets
        trimmed.append(candidate)
    return trimmed


def _normalize_confidence(value: Any) -> int:
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return 1
    if isinstance(value, bool):
        return 1
    if isinstance(value, (int, float)):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return max(1, min(5, round(1 + numeric * 4)))
        return max(1, min(5, round(numeric)))
    return 1


def _normalize_solver_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    normalized["confidence"] = _normalize_confidence(normalized.get("confidence"))
    return normalized


POLICY_PAGE_NAME = "policy-contract.md"
RUNTIME_RULES_PAGE_NAME = "RUNTIME_RULES.md"


def _ensure_front_page(
    front_page_name: str,
    pages_used: list[str],
    pages: list["PageSummary"],
    *,
    include_content: bool,
    content_for_page: Callable[[WikiPage], str | None] | None = None,
) -> tuple[list[str], list["PageSummary"]]:
    """Ensure a given page is always included first in pages_used and pages."""
    if content_for_page is None:
        content_for_page = store.clean_content_for_model
    pages_used = [front_page_name, *[name for name in pages_used if name != front_page_name]]

    pages_by_name = {page.page_name: page for page in pages}
    if front_page_name not in pages_by_name:
        page = store.read_page(front_page_name)
        pages_by_name[front_page_name] = PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=content_for_page(page) if include_content else None,
        )

    ordered_pages: list[PageSummary] = [pages_by_name[front_page_name]]
    ordered_pages.extend(page for page in pages if page.page_name != front_page_name)
    return pages_used, ordered_pages


def _expand_related_summaries(
    selected_page_names: list[str],
    *,
    max_neighbors: int,
    max_total_chars: int,
) -> list[dict[str, Any]]:
    """Return short context blocks for curated related neighbors of selected pages."""
    already_selected = set(selected_page_names)
    allowed = store.allowed_page_names()
    candidates: list[str] = []
    seen_candidates: set[str] = set()

    for page_name in selected_page_names:
        try:
            page = store.read_page(page_name)
        except FileNotFoundError:
            continue
        for ref in page.related:
            match = _WIKI_LINK_RE.search(ref)
            if not match:
                continue
            target = f"{match.group(1)}.md"
            if target in already_selected or target in seen_candidates or target not in allowed:
                continue
            seen_candidates.add(target)
            candidates.append(target)

    blocks: list[dict[str, Any]] = []
    total_chars = 0
    for candidate in candidates:
        if len(blocks) >= max_neighbors:
            break
        try:
            neighbor = store.read_page(candidate)
        except FileNotFoundError:
            continue
        summary_text = neighbor.summary or "(no summary available; see full page for details)"
        content = (
            "[RELATED CONTEXT - summary-only neighbor page.]\n"
            f"Title: {neighbor.title}\n"
            f"{summary_text}"
        )
        if total_chars + len(content) > max_total_chars and blocks:
            break
        blocks.append({"page_name": neighbor.name, "content": content, "expansion": True})
        total_chars += len(content)
    return blocks


def _normalize_ask_citations(raw_citations: list[Any], allowed_pages: set[str]) -> list[str]:
    citations: list[str] = []
    for raw_citation in raw_citations:
        if not isinstance(raw_citation, str):
            continue
        citation = raw_citation.strip()
        if not citation:
            continue
        if not citation.endswith(".md"):
            citation = f"{citation}.md"
        citation = store.normalize_page_name(citation)
        if citation in allowed_pages:
            citations.append(citation)
    return list(dict.fromkeys(citations))


def _effective_context_candidates(request: ContextPackRequest) -> tuple[list[dict[str, Any]], str]:
    if request.candidate_hints:
        return _plain_models(request.candidate_hints), "candidate_hints"
    legacy_candidates = request.__dict__.get("candidates", [])
    if legacy_candidates:
        return _to_candidate_hints(legacy_candidates), "candidates->candidate_hints"
    return [], "none"


def _effective_policy_candidates(request: PolicyPackRequest) -> tuple[list[dict[str, Any]], str]:
    if request.candidates_trimmed:
        return _plain_models(request.candidates_trimmed), "candidates_trimmed"
    legacy_candidates = request.__dict__.get("candidates", [])
    if legacy_candidates:
        return _to_candidates_trimmed(legacy_candidates), "candidates->candidates_trimmed"
    return [], "none"


app = FastAPI(
    title="FoodEx2 Wiki API",
    version="0.2.0",
    description="Wiki-owned retrieval API for FoodEx2 guidance and validation knowledge.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/wiki/view", include_in_schema=False)
def wiki_viewer():
    return FileResponse(STATIC_DIR / "viewer.html", media_type="text/html")


@app.get("/wiki/graph-view", include_in_schema=False)
def wiki_graph_viewer():
    return FileResponse(STATIC_DIR / "graph.html", media_type="text/html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/wiki/index")
def get_index() -> dict[str, Any]:
    index = store.read_page("index.md")
    return {
        "page_name": index.name,
        "title": index.title,
        "summary": index.summary,
        "content": index.content,
    }


@app.get("/wiki/pages")
def list_pages() -> dict[str, Any]:
    pages = [
        {
            "page_name": page.name,
            "title": page.title,
            "summary": page.summary,
            "category": store.page_category(page.name),
            "sources": page.sources,
            "related": page.related,
        }
        for page in store.catalog()
    ]
    return {"pages": pages, "count": len(pages)}


@app.get("/wiki/pages/{page_name}")
def get_page(page_name: str, include_content: bool = Query(default=True)) -> dict[str, Any]:
    try:
        page = store.read_page(page_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "page_name": page.name,
        "title": page.title,
        "summary": page.summary,
        "sources": page.sources,
        "related": page.related,
        "content": page.content if include_content else None,
    }


@app.post(
    "/wiki/ask",
    response_model=AskResponse,
    summary="Ask a FoodEx2 guidance question",
    description=(
        "Send a natural language FoodEx2 coding question. The service selects relevant wiki "
        "pages, answers from those pages, and returns citations plus a trace."
    ),
)
def ask_question(request: AskRequest) -> AskResponse:
    request_started = time.perf_counter()
    logger.info(
        "ask_request %s",
        json.dumps(
            {
                "question": request.question,
                "max_pages": request.max_pages,
                "use_graph_expansion": request.use_graph_expansion,
            },
            ensure_ascii=False,
        ),
    )

    selector_start = time.perf_counter()
    selector = get_selector_runner()
    if request.max_pages != selector.max_pages:
        selector.max_pages = request.max_pages
    selector_payload = {
        "search_term": request.question,
        "deconstructed_query": {"question": request.question},
        "candidates": [],
        "context": {"endpoint": "wiki.ask"},
    }
    try:
        selection_result = selector.run(selector_payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    selector_total_ms = int((time.perf_counter() - selector_start) * 1000)

    page_read_start = time.perf_counter()
    selected_pages_raw = [store.read_page(page_name) for page_name in selection_result.pages_used]
    selected_page_contents = [
        {
            "page_name": page.name,
            "content": store.clean_content_for_model(page),
        }
        for page in selected_pages_raw
    ]
    page_read_ms = int((time.perf_counter() - page_read_start) * 1000)

    graph_expansion_start = time.perf_counter()
    expansion_blocks: list[dict[str, Any]] = []
    if request.use_graph_expansion:
        expansion_blocks = _expand_related_summaries(
            selection_result.pages_used,
            max_neighbors=8,
            max_total_chars=8000,
        )
    graph_expansion_ms = int((time.perf_counter() - graph_expansion_start) * 1000)

    expanded_page_names = [block["page_name"] for block in expansion_blocks]
    pages_used = list(dict.fromkeys([*selection_result.pages_used, *expanded_page_names]))
    answerer_input_pages = selected_page_contents + expansion_blocks

    expansion_content_by_page = {block["page_name"]: block["content"] for block in expansion_blocks}
    pages: list[PageSummary] = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=store.clean_content_for_model(page) if request.include_page_content else None,
        )
        for page in selected_pages_raw
    ]
    for page_name in expanded_page_names:
        try:
            page = store.read_page(page_name)
        except FileNotFoundError:
            continue
        pages.append(
            PageSummary(
                page_name=page.name,
                title=page.title,
                summary=page.summary,
                sources=page.sources,
                related=page.related,
                content=expansion_content_by_page.get(page.name)
                if request.include_page_content
                else None,
            )
        )

    answerer = get_answerer_runner()
    answerer_start = time.perf_counter()
    try:
        answer_result = answerer.run(question=request.question, pages=answerer_input_pages)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    answerer_total_ms = int((time.perf_counter() - answerer_start) * 1000)

    request_wall_time_ms = int((time.perf_counter() - request_started) * 1000)
    response = AskResponse(
        answer=answer_result.answer,
        citations=_normalize_ask_citations(answer_result.citations, set(pages_used)),
        pages_used=pages_used,
        pages=pages,
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm page selector + answerer",
            "retrieval": {
                "model": selector.model,
                "tool_trace": selection_result.tool_trace,
                "token_summary": selection_result.token_summary,
                "timing_summary": selection_result.timing_summary,
            },
            "graph_expansion": {
                "enabled": request.use_graph_expansion,
                "neighbors_added": expanded_page_names,
                "neighbors_count": len(expansion_blocks),
            },
            "answerer": {
                "model": answerer.model,
                "token_summary": answer_result.token_summary,
                "timing_summary": answer_result.timing_summary,
            },
            "total": {
                "request_wall_time_ms": request_wall_time_ms,
                "total_llm_calls": (
                    int(selection_result.token_summary["calls"])
                    + int(answer_result.token_summary["calls"])
                ),
                "total_tracked_tokens": (
                    int(selection_result.token_summary["total_tracked_tokens"])
                    + int(answer_result.token_summary["total_tracked_tokens"])
                ),
            },
            "phase_timings_ms": {
                "selector_total": selector_total_ms,
                "page_read": page_read_ms,
                "graph_expansion": graph_expansion_ms,
                "answerer_total": answerer_total_ms,
            },
        },
    )
    logger.info(
        "ask_response %s",
        json.dumps(
            {
                "question": request.question,
                "answer_length": len(response.answer),
                "citations": response.citations,
                "pages_used": response.pages_used,
                "total_trace": response.trace["total"],
            },
            ensure_ascii=False,
        ),
    )
    return response


@app.get(
    "/wiki/graph",
    response_model=WikiGraphResponse,
    summary="Return the generated wiki adjacency map",
)
def get_wiki_graph() -> WikiGraphResponse:
    graph = store.graph_data()
    return WikiGraphResponse(
        nodes=[GraphNode(**node) for node in graph["nodes"]],
        edges=[GraphEdge(**edge) for edge in graph["edges"]],
        summary=GraphSummary(**graph["summary"]),
    )


@app.get(
    "/wiki/graph/compact",
    response_model=CompactWikiGraphResponse,
    summary="Return a frontend-friendly compact wiki graph",
)
def get_compact_wiki_graph() -> CompactWikiGraphResponse:
    graph = store.compact_graph_data()
    return CompactWikiGraphResponse(
        nodes=[CompactGraphNode(**node) for node in graph["nodes"]],
        edges=[CompactGraphEdge(**edge) for edge in graph["edges"]],
        summary=GraphSummary(**graph["summary"]),
    )


@app.get(
    "/wiki/pages/{page_name}/backlinks",
    response_model=BacklinksResponse,
    summary="Return backlinks for one wiki page",
)
def get_page_backlinks(page_name: str) -> BacklinksResponse:
    try:
        backlinks = store.page_backlinks(page_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BacklinksResponse(
        page_name=backlinks["page_name"],
        title=backlinks["title"],
        summary=backlinks["summary"],
        backlinks=[BacklinkEntry(**entry) for entry in backlinks["backlinks"]],
        backlink_count=backlinks["backlink_count"],
    )


@app.post(
    "/wiki/policy-pack",
    response_model=PolicyPackResponse,
    summary="Return selected wiki pages plus a synthesized policy pack",
    description=(
        "Use this when the wiki service should retrieve pages and synthesize a reasoning pack, "
        "but should not return the final FoodEx2 code. Preferred request field: "
        "`candidates_trimmed`. Include only `code`, `name`, `termType`, optional `coverageText`, "
        "and optional `implicitFacets`. Legacy full `candidates` input is still accepted, but "
        "the service reduces it internally before the librarian LLM call."
    ),
)
def create_policy_pack(request: PolicyPackRequest) -> PolicyPackResponse:
    request_started = time.perf_counter()
    effective_candidates, candidate_input_mode = _effective_policy_candidates(request)
    policy_contract = PolicyContract(**build_policy_contract())
    logger.info(
        "policy_pack_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
                "candidate_input_mode": candidate_input_mode,
                "candidate_count": len(effective_candidates),
                "context": request.context,
                "max_pages": request.max_pages,
            },
            ensure_ascii=False,
        ),
    )
    runner = get_librarian_runner()
    if request.max_pages != runner.max_pages:
        # v1 keeps the wrapper and prompt caps aligned.
        runner.max_pages = request.max_pages
    payload = {
        "search_term": request.search_term,
        "deconstructed_query": request.deconstructed_query,
        "candidates": effective_candidates,
        "context": request.context,
    }
    try:
        librarian_result = runner.run(payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pages = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=store.clean_content_for_model(page) if request.include_page_content else None,
        )
        for page in [store.read_page(page_name) for page_name in librarian_result.data["pages_used"]]
    ]
    final_pages_used, pages = _ensure_front_page(
        POLICY_PAGE_NAME,
        librarian_result.data["pages_used"], pages, include_content=request.include_page_content,
    )
    response = PolicyPackResponse(
        guiding_principles=store.guiding_principles(),
        policy_contract=policy_contract,
        pages_used=final_pages_used,
        pages=pages,
        query_classification=QueryClassification(**librarian_result.data["query_classification"]),
        candidate_focus=CandidateFocus(**librarian_result.data["candidate_focus"]),
        policy_pack=PolicyPackBody(**librarian_result.data["policy_pack"]),
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm librarian",
            "candidate_input_mode": candidate_input_mode,
            "tool_trace": librarian_result.tool_trace,
            "token_summary": librarian_result.token_summary,
            "timing_summary": {
                **librarian_result.timing_summary,
                "request_wall_time_ms": int((time.perf_counter() - request_started) * 1000),
            },
            "model": runner.model,
        },
    )
    logger.info(
        "policy_pack_response %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "guiding_principles_count": len(response.guiding_principles),
                "policy_version": response.policy_contract.policy_version,
                "pages_used": response.pages_used,
                "query_classification": response.query_classification.model_dump(),
                "candidate_focus": response.candidate_focus.model_dump(),
                "policy_pack": response.policy_pack.model_dump(),
                "token_summary": librarian_result.token_summary,
                "timing_summary": response.trace["timing_summary"],
            },
            ensure_ascii=False,
        ),
    )
    return response


@app.post(
    "/wiki/context-pack",
    response_model=ContextPackResponse,
    summary="Return selected wiki pages as prompt-facing context without synthesized rules",
    description=(
        "Use this when the wiki service should choose and return prompt-ready context pages "
        "without synthesizing a policy pack or final code. Page metadata is returned for "
        "traceability, while `content` is projected for runtime prompts and excludes "
        "orientation, maintenance, and navigation-only sections. Preferred request field: "
        "`candidate_hints`. Keep it minimal with only `code`, `name`, and `termType`."
    ),
)
def create_context_pack(request: ContextPackRequest) -> ContextPackResponse:
    request_started = time.perf_counter()
    effective_candidates, candidate_input_mode = _effective_context_candidates(request)
    policy_contract = PolicyContract(**build_policy_contract())
    logger.info(
        "context_pack_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
                "candidate_input_mode": candidate_input_mode,
                "candidate_count": len(effective_candidates),
                "context": request.context,
                "max_pages": request.max_pages,
            },
            ensure_ascii=False,
        ),
    )
    runner = get_selector_runner()
    if request.max_pages != runner.max_pages:
        runner.max_pages = request.max_pages
    payload = {
        "search_term": request.search_term,
        "deconstructed_query": request.deconstructed_query,
        "candidates": effective_candidates,
        "context": request.context,
    }
    try:
        selection_result = runner.run(payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pages = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=store.prompt_content_for_context_pack(page) if request.include_page_content else None,
        )
        for page in [store.read_page(page_name) for page_name in selection_result.pages_used]
    ]
    final_pages_used, pages = _ensure_front_page(
        RUNTIME_RULES_PAGE_NAME,
        selection_result.pages_used,
        pages,
        include_content=request.include_page_content,
        content_for_page=store.prompt_content_for_context_pack,
    )
    response = ContextPackResponse(
        guiding_principles=store.guiding_principles(),
        policy_contract=policy_contract,
        pages_used=final_pages_used,
        pages=pages,
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm page selector",
            "candidate_input_mode": candidate_input_mode,
            "tool_trace": selection_result.tool_trace,
            "prompt_projection": {
                "content_mode": "classification_prompt",
                "omitted_page_categories": ["maintenance", "orientation"],
                "omitted_page_scaffolding": ["page titles", "page preambles"],
                "omitted_sections": [
                    "Appendix A2 Codes",
                    "Authority",
                    "How To Use This Page During Ingest",
                    "Orientation",
                    "Relevant Business Rules",
                    "Relevant Policy",
                    "Supporting Pages By Signal",
                    "Worked Examples",
                ],
            },
            "token_summary": selection_result.token_summary,
            "timing_summary": {
                **selection_result.timing_summary,
                "request_wall_time_ms": int((time.perf_counter() - request_started) * 1000),
            },
            "model": runner.model,
        },
    )
    logger.info(
        "context_pack_response %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "guiding_principles_count": len(response.guiding_principles),
                "policy_version": response.policy_contract.policy_version,
                "pages_used": response.pages_used,
                "token_summary": selection_result.token_summary,
                "timing_summary": response.trace["timing_summary"],
            },
            ensure_ascii=False,
        ),
    )
    return response


@app.post(
    "/wiki/solve",
    response_model=SolveResponse,
    summary="Return the final FoodEx2 coding result plus wiki context and trace",
    description=(
        "Use this when the wiki service should make the final FoodEx2 coding decision. This "
        "endpoint expects the full external candidate universe in the `candidates` field, "
        "because the solver chooses among candidates and constructs the final code."
    ),
)
def solve_foodex2(request: SolveRequest) -> SolveResponse:
    if not request.candidates:
        raise HTTPException(status_code=400, detail="solve requires a non-empty candidates list")

    request_started = time.perf_counter()
    policy_contract = PolicyContract(**build_policy_contract())
    logger.info(
        "solve_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
                "candidate_input_mode": "candidates",
                "candidate_count": len(request.candidates),
                "context": request.context,
                "max_pages": request.max_pages,
            },
            ensure_ascii=False,
        ),
    )

    librarian = get_librarian_runner()
    if request.max_pages != librarian.max_pages:
        librarian.max_pages = request.max_pages
    solver = get_solver_runner()
    plain_candidates = _plain_models(request.candidates)
    payload = {
        "search_term": request.search_term,
        "deconstructed_query": request.deconstructed_query,
        "candidates": plain_candidates,
        "context": request.context,
    }
    try:
        librarian_result = librarian.run(payload)
        raw_page_names = [POLICY_PAGE_NAME, *[name for name in librarian_result.data["pages_used"] if name != POLICY_PAGE_NAME]]
        pages_raw = [store.read_page(page_name) for page_name in raw_page_names]
        solver_payload = {
            "search_term": request.search_term,
            "deconstructed_query": request.deconstructed_query,
            "candidates": plain_candidates,
            "context": request.context,
            "guiding_principles": store.guiding_principles(),
            "policy_contract": policy_contract.model_dump(),
            "query_classification": librarian_result.data["query_classification"],
            "candidate_focus": librarian_result.data["candidate_focus"],
            "policy_pack": librarian_result.data["policy_pack"],
            "pages_used": raw_page_names,
            "pages": [
                {
                    "page_name": page.name,
                    "title": page.title,
                    "summary": page.summary,
                    "content": page.content,
                }
                for page in pages_raw
            ],
        }
        solver_result = solver.run(solver_payload)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pages = [
        PageSummary(
            page_name=page.name,
            title=page.title,
            summary=page.summary,
            sources=page.sources,
            related=page.related,
            content=store.clean_content_for_model(page) if request.include_page_content else None,
        )
        for page in pages_raw
    ]
    final_pages_used, pages = _ensure_front_page(
        POLICY_PAGE_NAME,
        librarian_result.data["pages_used"], pages, include_content=request.include_page_content,
    )

    response = SolveResponse(
        guiding_principles=store.guiding_principles(),
        policy_contract=policy_contract,
        pages_used=final_pages_used,
        pages=pages,
        query_classification=QueryClassification(**librarian_result.data["query_classification"]),
        candidate_focus=CandidateFocus(**librarian_result.data["candidate_focus"]),
        policy_pack=PolicyPackBody(**librarian_result.data["policy_pack"]),
        solution=SolveResultBody(**_normalize_solver_data(solver_result.data)),
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm librarian + solver",
            "candidate_input_mode": "candidates",
            "retrieval": {
                "model": librarian.model,
                "tool_trace": librarian_result.tool_trace,
                "token_summary": librarian_result.token_summary,
                "timing_summary": librarian_result.timing_summary,
            },
            "solver": {
                "model": solver.model,
                "token_summary": solver_result.token_summary,
                "timing_summary": solver_result.timing_summary,
            },
            "total": {
                "request_wall_time_ms": int((time.perf_counter() - request_started) * 1000),
                "total_llm_calls": (
                    int(librarian_result.token_summary["calls"])
                    + int(solver_result.token_summary["calls"])
                ),
                "total_tracked_tokens": (
                    int(librarian_result.token_summary["total_tracked_tokens"])
                    + int(solver_result.token_summary["total_tracked_tokens"])
                ),
            },
        },
    )
    logger.info(
        "solve_response %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "guiding_principles_count": len(response.guiding_principles),
                "policy_version": response.policy_contract.policy_version,
                "pages_used": response.pages_used,
                "constructed_code": response.solution.constructedCode,
                "retrieval_token_summary": librarian_result.token_summary,
                "solver_token_summary": solver_result.token_summary,
                "total_trace": response.trace["total"],
            },
            ensure_ascii=False,
        ),
    )
    return response
