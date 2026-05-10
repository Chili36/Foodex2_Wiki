from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Awaitable, Callable

from .clients import CatalogClient, SemanticSearchClient, ValidatorClient, WikiClient
from .models import ToolCallRecord
from .planning import plan_source_text


ToolHandler = Callable[[dict[str, Any]], Awaitable[Any]]


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "plan_foodex2_coding_strategy",
        "description": "Create a mission-first FoodEx2 coding strategy from the source text before searching for building blocks.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "source_text": {"type": "string"},
            },
            "required": ["source_text"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "wiki_ask_guidance",
        "description": "Ask the FoodEx2 wiki /wiki/ask endpoint for a grounded human-style guidance answer before searching for building blocks.",
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
        "name": "semantic_search_candidates",
        "description": "Search the Qdrant-backed FoodEx2 vector index for likely candidate codes. Use for recall only; verify candidates with catalogue and validator tools.",
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
        "name": "catalog_search_terms",
        "description": "Search the authoritative FoodEx2 catalogue/database for matrix terms.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "term_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional term types such as r, d, c, s, h, g, f, n.",
                },
                "domain": {"type": ["string", "null"]},
                "limit": {"type": "integer"},
            },
            "required": ["query", "term_types", "domain", "limit"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "catalog_get_term",
        "description": "Get authoritative FoodEx2 term details by code.",
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
        "name": "catalog_get_parents",
        "description": "Get parent hierarchy terms for a FoodEx2 code.",
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
        "name": "catalog_get_children",
        "description": "Get child terms for a FoodEx2 code.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "code": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["code", "limit"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "catalog_get_implicit_facets",
        "description": "Get implicit facets carried by a FoodEx2 base term.",
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
        "name": "catalog_search_facets",
        "description": "Search authoritative FoodEx2 facet descriptors and facet families.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "facet_type": {"type": ["string", "null"]},
                "limit": {"type": "integer"},
            },
            "required": ["query", "facet_type", "limit"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "wiki_context",
        "description": "Ask the FoodEx2 wiki API for prompt-ready rules relevant to the current case.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "search_term": {"type": "string"},
                "candidate_hints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "code": {"type": "string"},
                            "name": {"type": ["string", "null"]},
                            "termType": {"type": ["string", "null"]},
                            "type": {"type": ["string", "null"]},
                            "scopeNote": {"type": ["string", "null"]},
                            "coverageText": {"type": ["string", "null"]},
                        },
                        "required": [
                            "code",
                            "name",
                            "termType",
                            "type",
                            "scopeNote",
                            "coverageText",
                        ],
                    },
                },
                "domain": {"type": ["string", "null"]},
                "max_pages": {"type": "integer"},
            },
            "required": ["search_term", "candidate_hints", "domain", "max_pages"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "wiki_policy_pack",
        "description": "Ask the FoodEx2 wiki to synthesize a mission-level policy guide from the source text and a small verified candidate set. This is guidance, not the final code.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "search_term": {"type": "string"},
                "candidates_trimmed": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "code": {"type": "string"},
                            "name": {"type": "string"},
                            "termType": {"type": "string"},
                            "coverageText": {"type": ["string", "null"]},
                            "implicitFacets": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "facetType": {"type": "string"},
                                        "facetCode": {"type": "string"},
                                        "facetMeaning": {"type": ["string", "null"]},
                                    },
                                    "required": ["facetType", "facetCode", "facetMeaning"],
                                },
                            },
                        },
                        "required": [
                            "code",
                            "name",
                            "termType",
                            "coverageText",
                            "implicitFacets",
                        ],
                    },
                },
                "domain": {"type": ["string", "null"]},
                "max_pages": {"type": "integer"},
            },
            "required": ["search_term", "candidates_trimmed", "domain", "max_pages"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "wiki_read_page",
        "description": "Read a specific FoodEx2 wiki page by filename.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"page_name": {"type": "string"}},
            "required": ["page_name"],
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "validator_validate_code",
        "description": "Validate a constructed FoodEx2 code with the FoodEx2 validator API.",
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
        wiki: WikiClient,
        validator: ValidatorClient,
    ):
        self.catalog = catalog
        self.semantic = semantic
        self.wiki = wiki
        self.validator = validator
        self._usage_events: list[dict[str, Any]] = []
        self._accepted_validation: dict[str, Any] | None = None
        self._post_validation_search_count = 0

    def pop_usage_events(self) -> list[dict[str, Any]]:
        events = self._usage_events
        self._usage_events = []
        return events

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        result = await self.execute(name, arguments)
        return ToolCallRecord(name=name, arguments=arguments, result=result)

    async def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        handlers: dict[str, ToolHandler] = {
            "plan_foodex2_coding_strategy": self._plan_foodex2_coding_strategy,
            "wiki_ask_guidance": self._wiki_ask_guidance,
            "semantic_search_candidates": self._semantic_search_candidates,
            "catalog_search_terms": self._catalog_search_terms,
            "catalog_get_term": self._catalog_get_term,
            "catalog_get_parents": self._catalog_get_parents,
            "catalog_get_children": self._catalog_get_children,
            "catalog_get_implicit_facets": self._catalog_get_implicit_facets,
            "catalog_search_facets": self._catalog_search_facets,
            "wiki_context": self._wiki_context,
            "wiki_policy_pack": self._wiki_policy_pack,
            "wiki_read_page": self._wiki_read_page,
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

    async def _plan_foodex2_coding_strategy(self, args: dict[str, Any]) -> Any:
        return plan_source_text(args["source_text"])

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
            "note": "Guidance answer from FoodEx2 wiki RAG. Source page metadata is omitted from agent-facing output.",
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

    async def _catalog_search_terms(self, args: dict[str, Any]) -> Any:
        limit = min(max(int(args.get("limit", 25)), 1), 100)
        result = await self.catalog.search_terms(
            query=args["query"],
            term_types=args.get("term_types") or None,
            domain=args.get("domain"),
            limit=limit,
        )
        return self._annotate_post_validation_search_result(
            result,
            query=args["query"],
        )

    async def _catalog_get_term(self, args: dict[str, Any]) -> Any:
        return await self.catalog.get_term(args["code"])

    async def _catalog_get_parents(self, args: dict[str, Any]) -> Any:
        return await self.catalog.get_parents(args["code"])

    async def _catalog_get_children(self, args: dict[str, Any]) -> Any:
        limit = min(max(int(args.get("limit", 50)), 1), 100)
        return await self.catalog.get_children(args["code"], limit=limit)

    async def _catalog_get_implicit_facets(self, args: dict[str, Any]) -> Any:
        return await self.catalog.get_implicit_facets(args["code"])

    async def _catalog_search_facets(self, args: dict[str, Any]) -> Any:
        limit = min(max(int(args.get("limit", 25)), 1), 100)
        result = await self.catalog.search_facets(
            query=args["query"],
            facet_type=args.get("facet_type"),
            limit=limit,
        )
        return self._annotate_post_validation_search_result(
            result,
            query=args["query"],
        )

    async def _wiki_context(self, args: dict[str, Any]) -> Any:
        max_pages = min(max(int(args.get("max_pages", 10)), 1), 15)
        result = await self.wiki.context_pack(
            search_term=args["search_term"],
            candidate_hints=args.get("candidate_hints") or [],
            domain=args.get("domain"),
            max_pages=max_pages,
        )
        return self._annotate_post_validation_search_result(
            result,
            query=args["search_term"],
        )

    async def _wiki_policy_pack(self, args: dict[str, Any]) -> Any:
        max_pages = min(max(int(args.get("max_pages", 6)), 1), 10)
        result = await self.wiki.policy_pack(
            search_term=args["search_term"],
            candidates_trimmed=args.get("candidates_trimmed") or [],
            domain=args.get("domain"),
            max_pages=max_pages,
        )
        return self._annotate_post_validation_search_result(
            result,
            query=args["search_term"],
        )

    async def _wiki_read_page(self, args: dict[str, Any]) -> Any:
        return await self.wiki.read_page(args["page_name"])

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
            annotated["agentHint"] = (
                "This code validates with no hard warnings. Validation is evidence, not "
                "permission to forget source facts. Build the best complete code now, "
                "classifying remaining facts as implicit, explicitly coded, unsupported, "
                "or not codeable rather than doing broad follow-up searches."
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
                f"Post-validation search {self._post_validation_search_count}: no exact "
                f"descriptor was found for '{query}'. The draft code already validates; "
                "classify this source fact as unsupported/not coded unless another tool "
                "result already proves an exact descriptor."
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
