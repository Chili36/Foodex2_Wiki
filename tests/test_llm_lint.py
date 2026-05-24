from __future__ import annotations

import json
from pathlib import Path

from wiki_api.llm_lint import AnthropicWikiLinter, build_lint_payload


REPO_ROOT = Path(__file__).resolve().parent.parent


def _response(*, text: str, input_tokens: int = 100, output_tokens: int = 50) -> dict[str, object]:
    return {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": text}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
    }


class FakeMessages:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response: dict[str, object]) -> None:
        self.messages = FakeMessages(response)


def test_lint_payload_includes_doctor_report_and_prompt_projection() -> None:
    payload = build_lint_payload(
        root=REPO_ROOT,
        page_names=["facet-coding-rules.md"],
        focus="F09 examples",
    )

    assert payload["focus"] == "F09 examples"
    assert payload["doctor_report"]["error_count"] == 0
    assert payload["selected_pages"] == ["facet-coding-rules.md"]
    assert payload["pages"][0]["page_name"] == "facet-coding-rules.md"
    assert payload["pages"][0]["prompt_facing"] is True
    assert "Worked Examples" in payload["pages"][0]["raw_content"]
    assert "Worked Examples" not in payload["pages"][0]["prompt_projection"]
    assert "# Index" in payload["wiki_index"]


def test_linter_returns_markdown_report_and_usage_trace() -> None:
    report = "## Verdict\n\nNo material findings."
    client = FakeAnthropicClient(_response(text=report, input_tokens=321, output_tokens=45))
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    result = AnthropicWikiLinter(client=client, model="fake-lint-model").run(payload)

    assert result.report == report
    assert result.pages_linted == ["facet-coding-rules.md"]
    assert result.token_summary["model"] == "fake-lint-model"
    assert result.token_summary["total_tracked_tokens"] == 366
    assert result.timing_summary["calls"] == 1

    call = client.messages.calls[0]
    assert call["model"] == "fake-lint-model"
    assert "wiki lint reviewer" in str(call["system"])
    message_payload = json.loads(call["messages"][0]["content"])
    assert message_payload["selected_pages"] == ["facet-coding-rules.md"]
