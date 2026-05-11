from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from .agent import FoodEx2Agent
from .clients import CatalogClient, SemanticSearchClient, ValidatorClient
from .models import CodeRequest, CodeResponse
from .settings import settings
from .tools import FoodEx2Toolbox


STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_BUILD = "tight-4tool-v1"


def build_toolbox() -> FoodEx2Toolbox:
    return FoodEx2Toolbox(
        catalog=CatalogClient(settings),
        semantic=SemanticSearchClient(settings),
        validator=ValidatorClient(settings),
    )


def build_agent() -> FoodEx2Agent:
    return FoodEx2Agent(settings=settings, toolbox=build_toolbox())


app = FastAPI(
    title="FoodEx2 Agent App",
    version="0.1.0",
    description="Tool-using FoodEx2 coding agent backed by catalogue, wiki, and validator APIs.",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    response = FileResponse(STATIC_DIR / "index.html", media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "build": APP_BUILD,
        "model": settings.openai_model,
        "utilityModel": settings.utility_model,
        "selfEvaluationModel": settings.self_evaluation_model,
        "failureAnalysisModel": settings.failure_analysis_model,
        "modelOptions": settings.model_option_list,
        "toolReasonDebug": settings.tool_reason_debug,
        "postValidationToolBudget": settings.post_validation_tool_budget,
        "wikiApiUrl": settings.wiki_api_url,
        "catalogApiUrl": settings.catalog_api_url,
        "validatorApiUrl": settings.validator_api_url,
        "semanticSearchUrl": settings.semantic_search_url,
        "semanticCollection": settings.semantic_collection,
    }


@app.post("/agent/code", response_model=CodeResponse)
async def code_foodex2(request: CodeRequest) -> CodeResponse:
    return await build_agent().run(request)


@app.post("/agent/code/stream")
async def code_foodex2_stream(request: CodeRequest) -> StreamingResponse:
    async def event_stream():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def sink(event: dict[str, Any]) -> None:
            await queue.put(event)

        async def runner() -> None:
            try:
                response = await build_agent().run(request, event_sink=sink)
                await queue.put({"event": "final", "response": _dump_model(response)})
            except Exception as exc:
                await queue.put({"event": "fatal_error", "error": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(runner())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield json.dumps(event, ensure_ascii=False, default=str) + "\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )


def _dump_model(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value
