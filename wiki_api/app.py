from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .librarian import (
    AnthropicFoodEx2Solver,
    AnthropicWikiLibrarian,
    AnthropicWikiPageSelector,
)
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


class PolicyPackRequest(BaseModel):
    search_term: str
    deconstructed_query: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    max_pages: int = Field(default=6, ge=1, le=10)
    include_page_content: bool = True


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


class PolicyPackResponse(BaseModel):
    guiding_principles: list[str]
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
    pages_used: list[str]
    pages: list[PageSummary]
    query_classification: QueryClassification
    candidate_focus: CandidateFocus
    policy_pack: PolicyPackBody
    solution: SolveResultBody
    trace: dict[str, Any]


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


app = FastAPI(
    title="FoodEx2 Wiki API",
    version="0.1.0",
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


@app.post("/wiki/policy-pack", response_model=PolicyPackResponse)
def create_policy_pack(request: PolicyPackRequest) -> PolicyPackResponse:
    request_started = time.perf_counter()
    logger.info(
        "policy_pack_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
                "candidate_count": len(request.candidates),
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
        "candidates": request.candidates,
        "context": request.context,
    }
    try:
        librarian_result = runner.run(payload)
    except RuntimeError as exc:
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
        pages_used=librarian_result.data["pages_used"],
        pages=pages,
        query_classification=QueryClassification(**librarian_result.data["query_classification"]),
        candidate_focus=CandidateFocus(**librarian_result.data["candidate_focus"]),
        policy_pack=PolicyPackBody(**librarian_result.data["policy_pack"]),
        trace={
            "index_used": True,
            "max_pages": request.max_pages,
            "selection_method": "service-owned llm librarian",
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


@app.post("/wiki/context-pack", response_model=ContextPackResponse)
def create_context_pack(request: PolicyPackRequest) -> ContextPackResponse:
    request_started = time.perf_counter()
    logger.info(
        "context_pack_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
                "candidate_count": len(request.candidates),
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
        "candidates": request.candidates,
        "context": request.context,
    }
    try:
        selection_result = runner.run(payload)
    except RuntimeError as exc:
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


@app.post("/wiki/solve", response_model=SolveResponse)
def solve_foodex2(request: PolicyPackRequest) -> SolveResponse:
    if not request.candidates:
        raise HTTPException(status_code=400, detail="solve requires a non-empty candidates list")

    request_started = time.perf_counter()
    logger.info(
        "solve_request %s",
        json.dumps(
            {
                "search_term": request.search_term,
                "deconstructed_query": request.deconstructed_query,
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
    except RuntimeError as exc:
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
