from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Awaitable, Callable

from .clients import CatalogClient, SemanticSearchClient, ValidatorClient, WikiClient
from .models import ToolCallRecord


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


# The 5-tool surface. Each tool maps to a clear ledger-advancing operation.
# Earlier versions exposed 13 tools mirroring the underlying wiki/catalogue/
# validator API surface; that turned every round into a 13-way decision and
# led to "stuck in tool calling". This trimmed surface keeps the production
# Stage-1 deconstructed search + the per-case wiki guidance ("how to code
# this") + the catalogue inspection + the validator gate + the targeted
# facet search.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "semantic_search_candidates",
        "description": "Deconstructed vector search (Qdrant): splits the query into base term + components, runs parallel searches, merges results with highest-score-wins per code. The primary recall tool — call first. If the right candidate still seems missing after inspection, refine the query and call once more.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query", "limit"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "wiki_ask_guidance",
        "description": "Ask the FoodEx2 wiki for case-specific coding guidance. Use after the first semantic search, BEFORE inspecting candidates: ask 'how should I code <verbatim source text>? which facet families apply to <listed source phrases>?'. The wiki returns prose advice naming the relevant facet families (F10, F21, F27, F28, F04 etc.) and any business rules that apply. This is per-case guidance — call it once, with the source text and the top 2-3 candidate codes you got back.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "question": {"type": "string"},
            },
            "required": ["question"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "catalog_get_term",
        "description": "Authoritative term details for a FoodEx2 code: name, term type, scope note, hierarchies (parents), implicit facets, monitoring flags. Use this to inspect a candidate before committing to it as the base.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "validator_validate_code",
        "description": "Validate a constructed FoodEx2 code against the validator. Clean validation is the gate to finalize; hard warnings drive one targeted repair attempt; soft warnings are advisory.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "code": {"type": "string"},
                "domain": {"type": ["string", "null"]},
                "context": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Optional validator options; use validatorContext such as ICT only if explicitly known.",
                    "properties": {
                        "validatorContext": {"type": ["string", "null"]},
                    },
                    "required": ["validatorContext"],
                },
            },
            "required": ["code", "domain", "context"],
        },
        "strict": True,
    },
]


def build_tool_definitions(*, include_debug_why: bool = False) -> list[dict[str, Any]]:
    tools = deepcopy(TOOL_DEFINITIONS)
    if include_debug_why:
        _attach_debug_why_fields(tools)
    return tools


def _attach_debug_why_fields(tools: list[dict[str, Any]]) -> None:
    for tool in tools:
        parameters = tool.get("parameters")
        if not isinstance(parameters, dict):
            continue
        properties = parameters.setdefault("properties", {})
        properties["why"] = {
            "type": "string",
            "description": (
                "Debug-only visible reason for this tool call: expected answer, "
                "source fact, and fallback if empty."
            ),
        }
        required = parameters.setdefault("required", [])
        if "why" not in required:
            required.append("why")


class FoodEx2Toolbox:
    def __init__(
        self,
        *,
        catalog: CatalogClient,
        semantic: SemanticSearchClient,
        validator: ValidatorClient,
        wiki: WikiClient,
    ):
        self.catalog = catalog
        self.semantic = semantic
        self.validator = validator
        self.wiki = wiki
        self._usage_events: list[dict[str, Any]] = []
        self._accepted_validation: dict[str, Any] | None = None
        self._post_validation_search_count = 0

    def reset_request_state(self) -> None:
        """Clear per-request state so a shared toolbox doesn't leak between agent runs.

        The earlier loop had a real bug where `agentHint` carried a stale
        `validatedDraft` from a prior case into a new one (see iter-1
        run_learning analysis). Callers should invoke this at the top of each
        `agent.run()`.
        """
        self._accepted_validation = None
        self._post_validation_search_count = 0
        self._usage_events = []

    def pop_usage_events(self) -> list[dict[str, Any]]:
        events = self._usage_events
        self._usage_events = []
        return events

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        result = await self.execute(name, arguments)
        return ToolCallRecord(name=name, arguments=arguments, result=result)

    async def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        handlers: dict[str, ToolHandler] = {
            "semantic_search_candidates": self._semantic_search_candidates,
            "wiki_ask_guidance": self._wiki_ask_guidance,
            "catalog_get_term": self._catalog_get_term,
            "validator_validate_code": self._validator_validate_code,
        }
        if name not in handlers:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handlers[name](arguments)
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def serialize_result(result: Any) -> str:
        return json.dumps(result, ensure_ascii=False, default=str)

    async def _wiki_ask_guidance(self, args: dict[str, Any]) -> Any:
        response = await self.wiki.ask(
            question=args["question"],
            max_pages=7,
            include_page_content=False,
        )
        if not isinstance(response, dict):
            return response
        self._capture_wiki_usage(response, tool_name="wiki_ask_guidance")
        return {
            "answer": response.get("answer", ""),
            "note": "Per-case guidance from the FoodEx2 wiki. Use the named facet families and rules; do not duplicate implicit facets already on the chosen base.",
        }

    def _capture_wiki_usage(self, response: dict[str, Any], *, tool_name: str) -> None:
        trace = response.get("trace")
        if not isinstance(trace, dict):
            return
        for stage_name in ("retrieval", "answerer"):
            stage = trace.get(stage_name)
            if not isinstance(stage, dict):
                continue
            summary = stage.get("token_summary")
            if not isinstance(summary, dict):
                continue
            self._usage_events.append(
                {
                    "source": f"{tool_name}.{stage_name}",
                    "model": summary.get("model") or stage.get("model"),
                    "calls": int(summary.get("calls") or 0),
                    "input_tokens": int(summary.get("input_tokens") or 0),
                    "output_tokens": int(summary.get("output_tokens") or 0),
                    "cache_creation_input_tokens": int(
                        summary.get("cache_creation_input_tokens") or 0
                    ),
                    "cache_read_input_tokens": int(summary.get("cache_read_input_tokens") or 0),
                    "total_tracked_tokens": int(summary.get("total_tracked_tokens") or 0),
                }
            )

    async def _semantic_search_candidates(self, args: dict[str, Any]) -> Any:
        limit = min(max(int(args.get("limit", 10)), 1), 25)
        result = await self.semantic.search_candidates(query=args["query"], limit=limit)
        return self._annotate_post_validation_search_result(
            result,
            query=args["query"],
        )

    async def _catalog_get_term(self, args: dict[str, Any]) -> Any:
        return await self.catalog.get_term(args["code"])

    async def _validator_validate_code(self, args: dict[str, Any]) -> Any:
        result = await self.validator.validate_code(
            code=args["code"],
            domain=args.get("domain"),
            context=args.get("context") or {},
        )
        if isinstance(result, dict) and self._validation_is_accepted(result):
            self._accepted_validation = {
                "code": result.get("cleanedCode") or result.get("code") or args["code"],
                "inputCode": args["code"],
                "description": result.get("interpretedDescription")
                or result.get("description")
                or result.get("name"),
            }
            annotated = dict(result)
            has_facets = "#" in str(args["code"])
            if has_facets:
                annotated["agentHint"] = (
                    "Full constructed code (with explicit facets) validates with no hard "
                    "warnings. This is the finalize gate — return the JSON now. Do not "
                    "broaden the search."
                )
            else:
                annotated["agentHint"] = (
                    "BASE term validates with no hard warnings — this is NOT the finalize "
                    "gate yet. You still owe an explicit_facet (or a not_codeable disposition) "
                    "for every source modifier not covered by the base's implicit facets. "
                    "Now: for each uncovered modifier, use the wiki-named descriptor code "
                    "directly if one was given, otherwise check semantic_search results for "
                    "a termType='f' candidate matching it. Construct the full code, then "
                    "validate again before returning."
                )
            return annotated
        return result

    def _validation_is_accepted(self, result: dict[str, Any]) -> bool:
        if result.get("valid") is True:
            return not result.get("hardWarnings")
        if result.get("passes") is True:
            return not any(self._is_hard_warning(warning) for warning in result.get("warnings", []))
        return False

    @staticmethod
    def _is_hard_warning(warning: Any) -> bool:
        if not isinstance(warning, dict):
            return False
        severity = str(warning.get("severity") or warning.get("level") or "").lower()
        return severity in {"hard", "error", "critical", "high"}

    def _annotate_post_validation_search_result(self, result: Any, *, query: str) -> Any:
        if self._accepted_validation is None:
            return result

        self._post_validation_search_count += 1
        count = self._result_item_count(result)
        if count == 0:
            hint = (
                f"Post-validation search {self._post_validation_search_count}: the catalogue "
                f"label search for '{query}' returned no exact match. NOTE: the catalogue "
                "search is literal/label-based and often misses facet descriptors named "
                "differently than the query (e.g., 'organic' vs 'Organically produced'). "
                "If a prior wiki_ask_guidance response named a specific facet descriptor "
                "code for this concept (e.g., F10.A077L), use that code directly as an "
                "explicit_facet — the wiki is authoritative. Only classify as not_codeable "
                "if neither the wiki nor any earlier tool result names a descriptor."
            )
        else:
            hint = (
                f"Post-validation search {self._post_validation_search_count}: use only "
                "exact, legally valid descriptors from this result. If the result is only "
                "approximate, keep the validated draft and explain the uncoded source fact."
            )
        if isinstance(result, dict):
            annotated = dict(result)
            annotated["agentHint"] = hint
            annotated["postValidationSearchCount"] = self._post_validation_search_count
            annotated["validatedDraft"] = self._accepted_validation
            return annotated
        return {
            "results": result,
            "agentHint": hint,
            "postValidationSearchCount": self._post_validation_search_count,
            "validatedDraft": self._accepted_validation,
        }

    @staticmethod
    def _result_item_count(result: Any) -> int:
        if isinstance(result, list):
            return len(result)
        if isinstance(result, dict):
            for key in ("results", "terms", "items", "facets", "pages"):
                value = result.get(key)
                if isinstance(value, list):
                    return len(value)
        return 0
