from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .librarian import (
    AnthropicFoodEx2Solver,
    AnthropicWikiLibrarian,
    AnthropicWikiPageSelector,
)
from .policy import build_policy_contract
from .wiki_store import WikiStore


REPO_ROOT = Path(__file__).resolve().parent.parent
store = WikiStore(REPO_ROOT)
librarian_runner: AnthropicWikiLibrarian | Any | None = None
selector_runner: AnthropicWikiPageSelector | Any | None = None
solver_runner: AnthropicFoodEx2Solver | Any | None = None
logger = logging.getLogger("wiki_api")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def get_librarian_runner() -> AnthropicWikiLibrarian | Any:
    global librarian_runner
    if librarian_runner is None:
        librarian_runner = AnthropicWikiLibrarian(store=store)
    return librarian_runner


def get_selector_runner() -> AnthropicWikiPageSelector | Any:
    global selector_runner
    if selector_runner is None:
        selector_runner = AnthropicWikiPageSelector(store=store)
    return selector_runner


def get_solver_runner() -> AnthropicFoodEx2Solver | Any:
    global solver_runner
    if solver_runner is None:
        solver_runner = AnthropicFoodEx2Solver()
    return solver_runner


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
    scopeNote: str | None = Field(
        default=None,
        description="Optional scope note used for base-term and facet reasoning.",
    )
    implicitFacets: list[CandidateFacet] = Field(
        default_factory=list,
        description="Optional implicit facets already carried by the candidate term.",
    )


class SolveCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str = Field(description="FoodEx2 code.")
    name: str = Field(description="FoodEx2 display name.")
    termType: str = Field(description="FoodEx2 term type such as r, d, c, s, h, g, or f.")
    scopeNote: str | None = Field(
        default=None,
        description="Optional scope note from candidate retrieval.",
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


class CommonRequestFields(BaseModel):
    search_term: str
    deconstructed_query: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    max_pages: int = Field(default=6, ge=1, le=10)
    include_page_content: bool = True


class ContextPackRequest(CommonRequestFields):
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
            "candidate hints before calling the LLM selector."
        ),
        deprecated=True,
    )


class PolicyPackRequest(CommonRequestFields):
    candidates_trimmed: list[CandidateTrimmed] = Field(
        default_factory=list,
        description=(
            "Preferred candidate input for /wiki/policy-pack. Include only fields needed for "
            "reasoning: code, name, termType, optional scopeNote, and optional implicitFacets."
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


class DecisionProcedureStep(BaseModel):
    step: int
    name: str
    instruction: str


class BindingRule(BaseModel):
    id: str
    when: str
    must: str | None = None
    must_not: str | None = None


class TieBreakRule(BaseModel):
    id: str
    when: str
    prefer: str


class AntiPattern(BaseModel):
    id: str
    pattern: str
    reject: bool = True


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
        if item.get("scopeNote"):
            candidate["scopeNote"] = item["scopeNote"]
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
    "/wiki/policy-pack",
    response_model=PolicyPackResponse,
    summary="Return selected wiki pages plus a synthesized policy pack",
    description=(
        "Use this when the wiki service should retrieve pages and synthesize a reasoning pack, "
        "but should not return the final FoodEx2 code. Preferred request field: "
        "`candidates_trimmed`. Include only `code`, `name`, `termType`, optional `scopeNote`, "
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
    response = PolicyPackResponse(
        guiding_principles=store.guiding_principles(),
        policy_contract=policy_contract,
        pages_used=librarian_result.data["pages_used"],
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
    summary="Return selected wiki pages as raw context without synthesized rules",
    description=(
        "Use this when the wiki service should only choose and return context pages. Preferred "
        "request field: `candidate_hints`. Keep it minimal with only `code`, `name`, and "
        "`termType`. Legacy full `candidates` input is still accepted, but the service reduces "
        "it internally to candidate hints before the selector LLM call."
    ),
)
def create_context_pack(request: ContextPackRequest) -> ContextPackResponse:
    request_started = time.perf_counter()
    effective_candidates, candidate_input_mode = _effective_context_candidates(request)
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
            content=store.clean_content_for_model(page) if request.include_page_content else None,
        )
        for page in [store.read_page(page_name) for page_name in selection_result.pages_used]
    ]
    response = ContextPackResponse(
        guiding_principles=store.guiding_principles(),
        pages_used=selection_result.pages_used,
        pages=pages,
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm page selector",
            "candidate_input_mode": candidate_input_mode,
            "tool_trace": selection_result.tool_trace,
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
    payload = {
        "search_term": request.search_term,
        "deconstructed_query": request.deconstructed_query,
        "candidates": request.candidates,
        "context": request.context,
    }
    try:
        librarian_result = librarian.run(payload)
        pages_raw = [store.read_page(page_name) for page_name in librarian_result.data["pages_used"]]
        solver_payload = {
            "search_term": request.search_term,
            "deconstructed_query": request.deconstructed_query,
            "candidates": request.candidates,
            "context": request.context,
            "guiding_principles": store.guiding_principles(),
            "policy_contract": policy_contract.model_dump(),
            "query_classification": librarian_result.data["query_classification"],
            "candidate_focus": librarian_result.data["candidate_focus"],
            "policy_pack": librarian_result.data["policy_pack"],
            "pages_used": librarian_result.data["pages_used"],
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

    response = SolveResponse(
        guiding_principles=store.guiding_principles(),
        policy_contract=policy_contract,
        pages_used=librarian_result.data["pages_used"],
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
