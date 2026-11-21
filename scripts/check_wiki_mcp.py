"""Exercise the real stdio adapter against a running local Wiki API."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from mcp import Client
from mcp.client.stdio import StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]


async def check(args: argparse.Namespace) -> dict:
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "with_models": args.with_models, "calls": []}
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "scripts/run_wiki_mcp.py"), "--api-url", args.api_url],
        cwd=ROOT,
    )
    async with Client(params, read_timeout_seconds=130) as client:
        tools = (await client.list_tools()).tools
        report["tools"] = [tool.name for tool in tools]
        assert set(report["tools"]) == {"search_guidance", "get_guidance_page", "get_coding_context", "ask_guidance"}
        assert all(tool.annotations.read_only_hint for tool in tools)

        async def call(name, arguments):
            started = time.perf_counter()
            result = await client.call_tool(name, arguments)
            if result.is_error:
                raise RuntimeError(f"{name}: {result.content[0].text}")
            data = result.structured_content
            assert isinstance(data, dict)
            assert data.get("knowledge_revision", "").startswith("sha256:"), "Restart the API to load revision metadata."
            item = {
                "tool": name,
                "arguments": arguments,
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "knowledge_revision": data["knowledge_revision"],
            }
            for field in ("page_name", "pages_used", "citations", "answer", "trace", "result_count"):
                if field in data:
                    item[field] = data[field]
            report["calls"].append(item)
            return data, item

        found, _ = await call("search_guidance", {"query": "BR13", "limit": 3})
        assert 0 < len(found["results"]) <= 3
        page, _ = await call("get_guidance_page", {"page_name": "business-rules.md"})
        assert "BR13" in page["content"] and page["sources"]

        if args.with_models:
            dataset = json.loads((ROOT / "evals/wiki-rag/dmt_end_to_end_cases.json").read_text())
            reviewed = [case for case in dataset["cases"] if case.get("reviewed")][:4]
            assert reviewed
            for case in reviewed:
                pack, item = await call("get_coding_context", {
                    "search_term": case["question"],
                    "context": {"reporting_domain": case["domain"]},
                    "max_pages": 7,
                })
                assert pack["pages_used"][0] == "RUNTIME_RULES.md"
                assert len(pack["pages_used"]) == len(pack["pages"]) <= 7
                assert all(page["content"] for page in pack["pages"])
                assert pack["policy_contract"]["policy_version"]
                # Informational retrieval observations, not a new quality benchmark:
                # the reference pages were reviewed for ask, not context-pack.
                required = set(case["reference_pages"])
                item["case_id"] = case["id"]
                item["missing_reference_pages"] = sorted(required - set(pack["pages_used"]))
                item["reference_page_recall"] = len(required & set(pack["pages_used"])) / len(required)

            brief, _ = await call("ask_guidance", {
                "question": reviewed[0]["request_question"], "max_pages": 7,
            })
            assert brief["answer"] and brief["citations"]
            assert set(brief["citations"]) <= set(brief["pages_used"])
            assert len(brief["pages_used"]) <= 7

    report["transport_and_contract_checks"] = "passed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8010")
    parser.add_argument("--with-models", action="store_true", help="Make four paid selection calls and one paid guidance request using the API's configured providers.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(check(args))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"MCP checks passed. Report: {args.output}")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
