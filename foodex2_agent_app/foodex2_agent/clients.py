from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlparse

import httpx

from .settings import Settings


class ApiClientError(RuntimeError):
    pass


class JsonApiClient:
    def __init__(self, base_url: str, *, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get(path, params=_clean_params(params or {}))
        return _checked_json(response)

    async def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post(path, json=payload)
        return _checked_json(response)


class AbsoluteJsonApiClient:
    def __init__(self, url: str, *, timeout: float = 60.0):
        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.path = parsed.path or "/"
        self.timeout = timeout

    async def post_json(self, payload: dict[str, Any]) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.post(self.path, json=payload)
        return _checked_json(response)


def _checked_json(response: httpx.Response) -> Any:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ApiClientError(
            f"{response.request.method} {response.request.url} failed: "
            f"{response.status_code} {response.text[:500]}"
        ) from exc
    return response.json()


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, list):
            clean[key] = ",".join(str(item) for item in value)
        else:
            clean[key] = value
    return clean


def _path(template: str, *, code: str | None = None) -> str:
    if not template:
        return ""
    if code is None:
        return template
    return template.format(code=quote(code, safe=""))


def _result_items(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        for key in ("terms", "results", "items", "facets"):
            value = result.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _with_items(result: Any, key: str, items: list[dict[str, Any]]) -> Any:
    if isinstance(result, list):
        return items
    if isinstance(result, dict):
        patched = dict(result)
        for candidate_key in ("terms", "results", "items", "facets"):
            if isinstance(patched.get(candidate_key), list):
                patched[candidate_key] = items
                return patched
        patched[key] = items
        return patched
    return {key: items, "raw": result}


def _term_type(item: dict[str, Any]) -> str | None:
    value = item.get("termType") or item.get("term_type") or item.get("type")
    return str(value) if value is not None else None


def _search_type_for_terms(term_types: list[str] | None) -> str:
    if not term_types:
        return "baseTerm"
    normalized = {term_type.lower() for term_type in term_types}
    if normalized == {"f"}:
        return "facet"
    if "f" in normalized or "h" in normalized:
        return "all"
    return "baseTerm"


def _filter_by_term_type(result: Any, term_types: list[str] | None) -> Any:
    if not term_types:
        return result
    wanted = {term_type.lower() for term_type in term_types}
    items = [
        item
        for item in _result_items(result)
        if (_term_type(item) or "").lower() in wanted
    ]
    return _with_items(result, "terms", items)


def _limit_result(result: Any, *, key: str, limit: int) -> Any:
    items = _result_items(result)
    if not items or len(items) <= limit:
        return result
    return _with_items(result, key, items[:limit])


def _filter_facets(result: Any, facet_type: str | None) -> Any:
    if not facet_type:
        return result
    wanted = facet_type.lower()
    items = []
    for item in _result_items(result):
        group = (
            item.get("facetType")
            or item.get("facet_type")
            or item.get("facet_group")
            or item.get("groupId")
        )
        if group is not None and str(group).lower() == wanted:
            items.append(item)
    return _with_items(result, "facets", items)


class WikiClient:
    def __init__(self, settings: Settings):
        self.http = JsonApiClient(settings.wiki_api_url)

    async def ask(
        self,
        *,
        question: str,
        max_pages: int = 7,
        include_page_content: bool = False,
    ) -> Any:
        return await self.http.post_json(
            "/wiki/ask",
            {
                "question": question,
                "max_pages": max_pages,
                "include_page_content": include_page_content,
                "use_graph_expansion": True,
            },
        )

    async def context_pack(
        self,
        *,
        search_term: str,
        candidate_hints: list[dict[str, Any]] | None = None,
        domain: str | None = None,
        max_pages: int = 10,
    ) -> Any:
        return await self.http.post_json(
            "/wiki/context-pack",
            {
                "search_term": search_term,
                "candidate_hints": candidate_hints or [],
                "context": {"domain": domain} if domain else {},
                "max_pages": max_pages,
                "include_page_content": True,
            },
        )

    async def policy_pack(
        self,
        *,
        search_term: str,
        candidates_trimmed: list[dict[str, Any]] | None = None,
        domain: str | None = None,
        max_pages: int = 6,
    ) -> Any:
        return await self.http.post_json(
            "/wiki/policy-pack",
            {
                "search_term": search_term,
                "candidates_trimmed": candidates_trimmed or [],
                "context": {"domain": domain} if domain else {},
                "max_pages": max_pages,
                "include_page_content": True,
            },
        )

    async def read_page(self, page_name: str) -> Any:
        return await self.http.get_json(f"/wiki/pages/{quote(page_name, safe='')}")

    async def backlinks(self, page_name: str) -> Any:
        return await self.http.get_json(f"/wiki/pages/{quote(page_name, safe='')}/backlinks")


class CatalogClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http = JsonApiClient(settings.catalog_api_url)

    async def search_terms(
        self,
        *,
        query: str,
        term_types: list[str] | None = None,
        domain: str | None = None,
        limit: int = 25,
    ) -> Any:
        limit = min(max(limit, 1), self.settings.tool_model_max_items)
        path = self.settings.catalog_search_terms_path
        if path == "/api/search":
            result = await self.http.get_json(
                path,
                {
                    "q": query,
                    "type": _search_type_for_terms(term_types),
                    "domain": domain,
                    "limit": limit,
                },
            )
            return _limit_result(_filter_by_term_type(result, term_types), key="terms", limit=limit)
        return await self.http.get_json(
            path,
            {"query": query, "term_types": term_types, "domain": domain, "limit": limit},
        )

    async def get_term(self, code: str) -> Any:
        return await self.http.get_json(_path(self.settings.catalog_get_term_path, code=code))

    async def get_parents(self, code: str) -> Any:
        path = _path(self.settings.catalog_get_parents_path, code=code)
        if path:
            return await self.http.get_json(path)
        term = await self.get_term(code)
        return {"code": code, "parents": term.get("hierarchies", []) if isinstance(term, dict) else []}

    async def get_children(self, code: str, limit: int = 50) -> Any:
        path = _path(self.settings.catalog_get_children_path, code=code)
        if not path:
            return {
                "code": code,
                "children": [],
                "limit": limit,
                "warning": "The configured FoodEx2 catalogue API does not expose a child-term endpoint.",
            }
        return await self.http.get_json(
            path, {"limit": limit}
        )

    async def get_implicit_facets(self, code: str) -> Any:
        path = _path(self.settings.catalog_get_implicit_facets_path, code=code)
        if path:
            return await self.http.get_json(path)
        term = await self.get_term(code)
        implicit = term.get("implicitFacets", []) if isinstance(term, dict) else []
        raw = term.get("implicitFacetsRaw") if isinstance(term, dict) else None
        return {"code": code, "implicitFacets": implicit, "implicitFacetsRaw": raw}

    async def search_facets(
        self,
        *,
        query: str,
        facet_type: str | None = None,
        limit: int = 25,
    ) -> Any:
        limit = min(max(limit, 1), self.settings.tool_model_max_items)
        path = self.settings.catalog_search_facets_path
        if path == "/api/search":
            result = await self.http.get_json(
                path,
                {"q": query, "type": "facet", "limit": limit},
            )
            return _limit_result(_filter_facets(result, facet_type), key="facets", limit=limit)
        return await self.http.get_json(
            path,
            {"query": query, "facet_type": facet_type, "limit": limit},
        )


class SemanticSearchClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http = AbsoluteJsonApiClient(settings.semantic_search_url)

    async def search_candidates(self, *, query: str, limit: int = 10) -> Any:
        limit = min(max(limit, 1), self.settings.tool_model_max_items)
        # Use the production Stage-1 path: deconstruct the query into base +
        # components and run parallel Qdrant searches, merging with highest-
        # score-wins per code. This is what the DMT production pipeline does
        # (see Chili36/DMT wiki: FoodEx2-Architecture).
        raw = await self.http.post_json(
            {
                "query": query,
                "collection": self.settings.semantic_collection,
                "limit": limit,
                "use_deconstructed_search": True,
                "deconstructor_method": "stored_prompt",
            }
        )
        results = []
        for item in raw.get("results", []) if isinstance(raw, dict) else []:
            metadata = item.get("metadata") or {}
            results.append(
                {
                    "score": item.get("score"),
                    "code": item.get("code") or metadata.get("base_term_code"),
                    "name": item.get("name") or metadata.get("base_term_name"),
                    "termType": metadata.get("term_type"),
                    "termTypeDescription": metadata.get("term_type_desc"),
                    "scopeNote": metadata.get("scope_note"),
                    "facetCode": metadata.get("facet_code"),
                    "facetName": metadata.get("facet_name"),
                    "implicitFacets": metadata.get("implicit_facets") or {},
                    "monitoringFlags": metadata.get("monitoring_flags") or {},
                    "source": "qdrant",
                }
            )
        deconstruction = (
            raw.get("deconstruction")
            or raw.get("deconstructed_query")
            or raw.get("query_components")
            if isinstance(raw, dict)
            else None
        )
        return {
            "query": raw.get("query", query) if isinstance(raw, dict) else query,
            "collection": raw.get("collection", self.settings.semantic_collection)
            if isinstance(raw, dict)
            else self.settings.semantic_collection,
            "found": raw.get("found", len(results)) if isinstance(raw, dict) else len(results),
            "deconstruction": deconstruction,
            "results": results,
            "note": "Deconstructed Qdrant recall (base term + components, parallel search). Verify any candidate with catalog_get_term and validator_validate_code.",
        }


class ValidatorClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http = JsonApiClient(settings.validator_api_url)

    async def validate_code(
        self,
        *,
        code: str,
        domain: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        validator_context = "ICT"
        if context:
            candidate_context = (
                context.get("validatorContext")
                or context.get("validator_context")
                or context.get("context")
            )
            if isinstance(candidate_context, str) and candidate_context:
                validator_context = candidate_context
        return await self.http.post_json(
            self.settings.validator_validate_path,
            {"code": code, "domain": domain, "context": validator_context},
        )
