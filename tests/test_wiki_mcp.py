from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

import httpx
import pytest

pytest.importorskip("mcp", reason="Install requirements-mcp.txt to test the optional adapter")

from mcp import Client
from mcp.client.stdio import StdioServerParameters

import wiki_api.app as api
from wiki_api.librarian import AnswerResult, PageSelectionResult
from wiki_mcp.server import create_server, validate_api_url


ROOT = Path(__file__).resolve().parents[1]


def test_discovery_exposes_only_the_four_read_only_tools():
    async def run():
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert set(tools) == {"search_guidance", "get_guidance_page", "get_coding_context", "ask_guidance"}
        for tool in tools.values():
            assert tool.annotations.read_only_hint is True
            assert tool.output_schema is not None
            assert not {"selector_model", "answerer_model", "api_url"} & tool.input_schema["properties"].keys()
        budget = tools["get_coding_context"].input_schema["properties"]["max_pages"]
        assert (budget["minimum"], budget["maximum"], budget["default"]) == (4, 10, 7)

    asyncio.run(run())


def test_search_and_fetch_match_api_and_preserve_sources():
    async def run():
        transport = httpx.ASGITransport(app=api.app)
        async with Client(create_server(transport=transport)) as client:
            result = await client.call_tool("search_guidance", {"query": "BR13", "limit": 2})
            assert not result.is_error
            found = result.structured_content
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
                expected = (await http.get("/wiki/search", params={"q": "BR13", "limit": 2})).json()
            assert found == expected
            assert 0 < len(found["results"]) <= 2
            assert found["knowledge_revision"].startswith("sha256:")
            result = await client.call_tool("get_guidance_page", {"page_name": "business-rules.md"})
            page = result.structured_content
            assert not result.is_error
            assert "BR13" in page["content"]
            assert page["sources"]
            # Preserve missing authority metadata as null; never invent a tier.
            assert page["source_tier"] == api.store.read_page("business-rules.md").source_tier
            assert page["knowledge_revision"] == found["knowledge_revision"]
            assert json.loads(result.content[0].text) == page

    asyncio.run(run())


class StubSelector:
    max_pages = 7
    model = "offline-selector"

    def __init__(self):
        self.calls = []

    def run(self, payload):
        self.calls.append((self.max_pages, payload))
        return PageSelectionResult(
            pages_used=[
                "base-term-selection.md", "term-type-facet-constraints.md",
                "implicit-vs-explicit-facets.md", "business-rules.md",
                "pesticides-foodex2.md", "process-facets.md", "packaging-facets.md",
            ][:self.max_pages],
            tool_trace=[], token_summary={"calls": 1, "total_tracked_tokens": 0}, timing_summary={},
        )


class StubAnswerer:
    model = "offline-answerer"

    def run(self, *, question, pages):
        return AnswerResult(
            answer="Consult the base-term guidance and validate the result.",
            citations=["base-term-selection.md"],
            token_summary={"calls": 1, "total_tracked_tokens": 0}, timing_summary={},
        )


def test_model_tools_preserve_api_contract_and_request_budgets(monkeypatch):
    selector = StubSelector()
    monkeypatch.setattr(api, "selector_runner", selector)
    monkeypatch.setattr(api, "ask_selector_runner", selector)
    monkeypatch.setattr(api, "answerer_runner", StubAnswerer())

    async def run():
        transport = httpx.ASGITransport(app=api.app)
        async with Client(create_server(transport=transport)) as client:
            result = await client.call_tool("get_coding_context", {
                "search_term": "Bordsdruvor – färsk frukt",
                "context": {"reporting_domain": "pesticides"},
                "candidate_hints": [{"code": "A01GR", "name": "Test candidate", "termType": "r"}],
                "max_pages": 4,
            })
            assert not result.is_error
            pack = result.structured_content
            assert pack["pages_used"][0] == "RUNTIME_RULES.md"
            assert len(pack["pages"]) == len(pack["pages_used"]) == 4
            assert pack["policy_contract"]["policy_version"]
            assert pack["knowledge_revision"].startswith("sha256:")
            assert all(p["content"] for p in pack["pages"])
            for page in pack["pages"]:
                source = api.store.read_page(page["page_name"])
                assert page["sources"] == source.sources
                assert page["content"] == api.store.prompt_content_for_context_pack(source)
            assert selector.calls[0][0] == 4
            assert selector.calls[0][1]["context"] == {"reporting_domain": "pesticides"}
            assert selector.calls[0][1]["candidates"][0]["termType"] == "r"
            assert selector.max_pages == 7  # Cached runner must not retain another request's cap.

            result = await client.call_tool("ask_guidance", {"question": "How should I select a base term?", "max_pages": 2})
            assert not result.is_error
            brief = result.structured_content
            assert brief["citations"] == ["base-term-selection.md"]
            assert len(brief["pages_used"]) == 2
            assert all(page["content"] is None for page in brief["pages"])
            assert brief["pages"][0]["sources"]
            assert brief["trace"]["total"]["total_llm_calls"] == 2
            assert brief["knowledge_revision"] == pack["knowledge_revision"]
            assert selector.max_pages == 7

    asyncio.run(run())


@pytest.mark.parametrize("name,arguments", [
    ("get_guidance_page", {"page_name": "../../.env"}),
    ("get_guidance_page", {"page_name": "https://example.com"}),
    ("search_guidance", {"query": "   "}),
    ("search_guidance", {"query": "BR13", "limit": 21}),
    ("get_coding_context", {"search_term": "apple", "max_pages": 3}),
    ("get_coding_context", {"search_term": "apple", "candidate_hints": [{"code": "x", "name": "x", "termType": "r", "extra": True}]}),
    ("ask_guidance", {"question": "apple", "max_pages": 11}),
])
def test_invalid_arguments_never_reach_api(name, arguments):
    def fail(request):
        pytest.fail("Invalid arguments reached the API")

    async def run():
        async with Client(create_server(transport=httpx.MockTransport(fail))) as client:
            result = await client.call_tool(name, arguments)
            assert result.is_error

    asyncio.run(run())


@pytest.mark.parametrize("status,body,expected", [
    (404, '{"detail":"private upstream message"}', "not found"),
    (422, '{"detail":"private upstream message"}', "rejected"),
    (503, '{"detail":"private upstream message"}', "credentials"),
    (429, '{"detail":"private upstream message"}', "rate limited"),
    (500, 'private upstream message', "HTTP 500"),
    (302, '', "HTTP 302"),
    (200, 'private upstream message', "invalid JSON"),
    (200, '[]', "unexpected response"),
])
def test_upstream_failures_are_actionable_tool_errors(status, body, expected):
    async def run():
        transport = httpx.MockTransport(lambda _: httpx.Response(status, content=body))
        async with Client(create_server(transport=transport)) as client:
            result = await client.call_tool("get_guidance_page", {"page_name": "missing.md"})
        assert result.is_error
        assert expected in result.content[0].text
        assert "private upstream message" not in result.content[0].text

    asyncio.run(run())


@pytest.mark.parametrize("error,expected", [(httpx.ConnectError, "Cannot reach"), (httpx.ReadTimeout, "may still be processing")])
def test_network_failures_are_not_retried(error, expected):
    calls = []

    def fail(request):
        calls.append(request)
        raise error("private connection details", request=request)

    async def run():
        async with Client(create_server(transport=httpx.MockTransport(fail))) as client:
            result = await client.call_tool("ask_guidance", {"question": "apple"})
        assert result.is_error
        assert expected in result.content[0].text
        assert "private connection details" not in result.content[0].text
        assert len(calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize("url", ["https://example.com", "http://127.0.0.1.evil.test", "http://user:pass@localhost", "http://localhost/path", "http://localhost/?token=secret", "http://localhost:0"])
def test_pilot_only_accepts_loopback_origins(url):
    with pytest.raises(ValueError):
        validate_api_url(url)


def test_stdio_launch_from_unrelated_working_directory(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "scripts/run_wiki_mcp.py")],
            cwd=tmp_path,
        )
        # Test both current and legacy client negotiation, over the real stdio transport.
        for mode in ("auto", "legacy"):
            async with Client(params, mode=mode, read_timeout_seconds=10) as client:
                assert len((await client.list_tools()).tools) == 4

    asyncio.run(run())
