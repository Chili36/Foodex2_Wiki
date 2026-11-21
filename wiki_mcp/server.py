from __future__ import annotations

import argparse
import math
import os
from typing import Annotated, Any
from urllib.parse import urlsplit

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


DEFAULT_API_URL = "http://127.0.0.1:8010"
DEFAULT_TIMEOUT = 120.0
QueryText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
PageName = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*\.md$", max_length=160),
]


class CandidateHint(BaseModel):
    """Minimal catalogue evidence, without caller-controlled model settings."""

    model_config = ConfigDict(extra="forbid")
    code: Annotated[str, Field(min_length=1, max_length=80)]
    name: Annotated[str, Field(min_length=1, max_length=500)]
    termType: Annotated[str, Field(min_length=1, max_length=20)]


def validate_api_url(value: str) -> str:
    """The unauthenticated pilot only connects to a local API."""
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("WIKI_MCP_API_URL has an invalid port.") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or port == 0
    ):
        raise ValueError("WIKI_MCP_API_URL must be a loopback HTTP origin, such as http://127.0.0.1:8010.")
    return value.rstrip("/")


def create_server(
    *,
    api_url: str = DEFAULT_API_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT,
    transport: httpx.AsyncBaseTransport | None = None,
) -> MCPServer:
    """Create an adapter; injectable HTTP transport supports offline contract tests."""
    api_url = validate_api_url(api_url)
    if not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 600:
        raise ValueError("MCP timeout must be between 1 and 600 seconds.")

    server = MCPServer(
        "foodex2-knowledge",
        version="0.1.0",
        instructions=(
            "FoodEx2 coding guidance and evidence, not authoritative catalogue lookup or final validation. "
            "Use search_guidance for words, phrases and rule IDs, then get_guidance_page for full evidence. "
            "Use get_coding_context when you will reason about a coding case yourself; it includes mandatory "
            "runtime rules and selected pages. Use ask_guidance for a prepared cited brief. "
            "Cite returned page names and sources, preserve distinctions between source authority levels, "
            "and do not invent codes. A missing search hit is not proof that no rule exists. "
            "Context selection and guidance answers use the API's configured model providers and can incur cost."
        ),
        log_level="WARNING",
    )

    async def request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        # No ambient proxies, redirects, provider credentials, or automatic retries.
        # In particular, retrying a timed-out model call can duplicate its cost.
        try:
            async with httpx.AsyncClient(
                base_url=api_url,
                timeout=httpx.Timeout(timeout_seconds, connect=5.0),
                trust_env=False,
                follow_redirects=False,
                transport=transport,
            ) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise ToolError(
                "The Wiki API timed out. The backend may still be processing the request; "
                "check its logs before repeating a model-backed call."
            ) from exc
        except httpx.RequestError as exc:
            raise ToolError(
                "Cannot reach the local Wiki API. Start it on port 8010 or check WIKI_MCP_API_URL."
            ) from exc

        if response.status_code == 404:
            raise ToolError("Wiki page not found. Use search_guidance and an exact returned page_name.")
        if response.status_code == 422:
            raise ToolError("The Wiki API rejected the request. Check the tool's input schema and page budget.")
        if response.status_code in {429, 503}:
            raise ToolError(
                "The Wiki API is unavailable or rate limited. Check the API's model credentials, "
                "provider access and logs before retrying."
            )
        if response.status_code != 200:
            raise ToolError(f"The Wiki API returned HTTP {response.status_code}. Check the API logs.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ToolError("The Wiki API returned invalid JSON. Check the API URL and server version.") from exc
        if not isinstance(payload, dict):
            raise ToolError("The Wiki API returned an unexpected response; expected a JSON object.")
        return payload

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    async def search_guidance(
        query: QueryText,
        limit: Annotated[int, Field(ge=1, le=20)] = 10,
    ) -> dict[str, Any]:
        """Find literal words, quoted phrases or BR rule IDs in the wiki. No model calls.

        Returns ranked snippets, exact page_name values and source authority levels.
        This is text search, not semantic retrieval; use get_coding_context for a coding case.
        """
        return await request("GET", "/wiki/search", params={"q": query, "limit": limit})

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
    async def get_guidance_page(page_name: PageName) -> dict[str, Any]:
        """Read a complete wiki page, including source references and related pages. No model calls.

        Use the exact .md filename from search or citations, for example business-rules.md.
        Content is the maintained source page; get_coding_context returns its prompt projection.
        """
        return await request("GET", f"/wiki/pages/{page_name}", params={"include_content": True})

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
    async def get_coding_context(
        search_term: QueryText,
        candidate_hints: Annotated[list[CandidateHint], Field(max_length=50)] = [],
        context: dict[str, Any] | None = None,
        deconstructed_query: dict[str, Any] | None = None,
        max_pages: Annotated[int, Field(ge=4, le=10)] = 7,
    ) -> dict[str, Any]:
        """Get evidence for your own FoodEx2 coding reasoning; uses the API's model page selector.

        Returns mandatory RUNTIME_RULES.md, selected prompt-ready guidance, policy contract,
        sources and trace. max_pages includes the runtime page and all mandatory backfills.
        Supply only known candidate codes/names/termTypes. Set context.reporting_domain only
        when explicitly known. Does not construct or validate a final FoodEx2 code.
        """
        return await request(
            "POST",
            "/wiki/context-pack",
            json={
                "search_term": search_term,
                "candidate_hints": [item.model_dump() for item in candidate_hints],
                "context": context or {},
                "deconstructed_query": deconstructed_query or {},
                "max_pages": max_pages,
                "include_page_content": True,
            },
        )

    @server.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
    async def ask_guidance(
        question: QueryText,
        max_pages: Annotated[int, Field(ge=1, le=10)] = 7,
    ) -> dict[str, Any]:
        """Get a concise, cited FoodEx2 guidance brief using the API's selector and answer model.

        Returns the answer, citations, page source metadata and usage/timing trace.
        Use get_coding_context instead when you need page evidence for your own reasoning.
        This is guidance, not authoritative catalogue lookup or final validation.
        """
        return await request(
            "POST",
            "/wiki/ask",
            json={
                "question": question,
                "max_pages": max_pages,
                "include_page_content": False,
                "use_graph_expansion": False,
            },
        )

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local read-only FoodEx2 MCP server (stdio).")
    parser.add_argument("--api-url", default=os.environ.get("WIKI_MCP_API_URL", DEFAULT_API_URL))
    parser.add_argument("--timeout", type=float, default=os.environ.get("WIKI_MCP_TIMEOUT_SECONDS", "120"))
    args = parser.parse_args()
    try:
        server = create_server(api_url=args.api_url, timeout_seconds=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
