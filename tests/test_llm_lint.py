from __future__ import annotations

import json
from pathlib import Path

import pytest

from wiki_api.llm_lint import (
    DEFAULT_LINT_MAX_TOKENS,
    DEFAULT_LINT_MAX_TOKENS_WITH_THINKING,
    AnthropicWikiLinter,
    WikiLintError,
    build_lint_payload,
)
from wiki_api.source_intake import (
    DEFAULT_SOURCE_INTAKE_MAX_TOKENS,
    DEFAULT_SOURCE_INTAKE_MAX_TOKENS_WITH_THINKING,
    AnthropicSourceIntakeReviewer,
    SourceIntakeError,
    build_source_intake_payload,
)


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


def _thinking_only_response(*, output_tokens: int = 4000) -> dict[str, object]:
    """A response where thinking consumed the whole budget, leaving no text."""
    return {
        "stop_reason": "max_tokens",
        "content": [{"type": "thinking", "thinking": "still reasoning..."}],
        "usage": {
            "input_tokens": 100,
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
    assert "thinking" not in call
    assert call["max_tokens"] == DEFAULT_LINT_MAX_TOKENS
    assert result.token_summary["thinking_enabled"] is False
    assert "wiki lint reviewer" in str(call["system"])
    message_payload = json.loads(call["messages"][0]["content"])
    assert message_payload["selected_pages"] == ["facet-coding-rules.md"]


def test_linter_can_disable_thinking() -> None:
    report = "## Verdict\n\nNo material findings."
    client = FakeAnthropicClient(_response(text=report))
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    AnthropicWikiLinter(
        client=client,
        model="fake-lint-model",
        thinking_enabled=False,
    ).run(payload)

    call = client.messages.calls[0]
    assert "thinking" not in call
    assert call["max_tokens"] == DEFAULT_LINT_MAX_TOKENS


def test_explicit_thinking_uses_larger_default_max_tokens() -> None:
    report = "## Verdict\n\nNo material findings."
    client = FakeAnthropicClient(_response(text=report))
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    AnthropicWikiLinter(
        client=client,
        model="fake-lint-model",
        thinking_enabled=True,
    ).run(payload)

    call = client.messages.calls[0]
    assert call["thinking"] == {"type": "adaptive"}
    assert call["max_tokens"] == DEFAULT_LINT_MAX_TOKENS_WITH_THINKING


def test_explicit_max_tokens_overrides_thinking_default() -> None:
    report = "## Verdict\n\nNo material findings."
    client = FakeAnthropicClient(_response(text=report))
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    AnthropicWikiLinter(client=client, model="fake-lint-model", max_tokens=1234).run(payload)

    assert client.messages.calls[0]["max_tokens"] == 1234


def test_linter_fails_loudly_when_thinking_consumes_whole_budget() -> None:
    client = FakeAnthropicClient(_thinking_only_response())
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    with pytest.raises(WikiLintError) as excinfo:
        AnthropicWikiLinter(
            client=client,
            model="fake-lint-model",
            thinking_enabled=True,
        ).run(payload)

    message = str(excinfo.value)
    assert "max_tokens" in message
    assert "--no-thinking" in message


def test_linter_fails_loudly_on_whitespace_only_text() -> None:
    client = FakeAnthropicClient(_response(text="   \n\t  "))
    payload = build_lint_payload(root=REPO_ROOT, page_names=["facet-coding-rules.md"])

    with pytest.raises(WikiLintError):
        AnthropicWikiLinter(client=client, model="fake-lint-model").run(payload)


def test_source_intake_payload_includes_source_and_existing_pages() -> None:
    payload = build_source_intake_payload(
        root=REPO_ROOT,
        source_file="raw/efsa-guidance/base-term-selection.md",
        source_tier="diagnostic",
        focus="impact on base-term workflow",
        page_names=["base-term-selection.md"],
        max_source_chars=1200,
        max_page_chars=1200,
    )

    assert payload["focus"] == "impact on base-term workflow"
    assert payload["source"]["file"] == "raw/efsa-guidance/base-term-selection.md"
    assert payload["source"]["source_tier"] == "diagnostic"
    assert "Base Term Selection" in payload["source"]["source_text"]
    assert payload["selected_existing_pages"][0]["page_name"] == "base-term-selection.md"
    assert payload["doctor_report"]["error_count"] == 0
    assert "# FoodEx2 Wiki Ingest Workflow" in payload["ingest_workflow"]


def test_source_intake_reviewer_uses_adaptive_thinking() -> None:
    report = "## Intake Verdict\n\nPatch existing pages."
    client = FakeAnthropicClient(_response(text=report, input_tokens=500, output_tokens=100))
    payload = build_source_intake_payload(
        root=REPO_ROOT,
        source_file="raw/efsa-guidance/base-term-selection.md",
        page_names=["base-term-selection.md"],
    )

    result = AnthropicSourceIntakeReviewer(
        client=client,
        model="fake-intake-model",
        thinking_enabled=True,
    ).run(payload)

    assert result.report == report
    assert result.source_file == "raw/efsa-guidance/base-term-selection.md"
    assert result.token_summary["model"] == "fake-intake-model"
    assert result.token_summary["thinking_enabled"] is True
    call = client.messages.calls[0]
    assert call["thinking"] == {"type": "adaptive"}
    assert "source-intake reviewer" in str(call["system"])
    assert call["max_tokens"] == DEFAULT_SOURCE_INTAKE_MAX_TOKENS_WITH_THINKING


def test_source_intake_defaults_to_no_thinking_and_smaller_max_tokens() -> None:
    report = "## Intake Verdict\n\nPatch existing pages."
    client = FakeAnthropicClient(_response(text=report))
    payload = build_source_intake_payload(
        root=REPO_ROOT,
        source_file="raw/efsa-guidance/base-term-selection.md",
        page_names=["base-term-selection.md"],
    )

    AnthropicSourceIntakeReviewer(
        client=client,
        model="fake-intake-model",
    ).run(payload)

    call = client.messages.calls[0]
    assert "thinking" not in call
    assert call["max_tokens"] == DEFAULT_SOURCE_INTAKE_MAX_TOKENS


def test_source_intake_explicit_max_tokens_overrides_default() -> None:
    report = "## Intake Verdict\n\nPatch existing pages."
    client = FakeAnthropicClient(_response(text=report))
    payload = build_source_intake_payload(
        root=REPO_ROOT,
        source_file="raw/efsa-guidance/base-term-selection.md",
        page_names=["base-term-selection.md"],
    )

    AnthropicSourceIntakeReviewer(
        client=client,
        model="fake-intake-model",
        max_tokens=4321,
    ).run(payload)

    assert client.messages.calls[0]["max_tokens"] == 4321


def test_source_intake_fails_loudly_when_thinking_consumes_whole_budget() -> None:
    client = FakeAnthropicClient(_thinking_only_response())
    payload = build_source_intake_payload(
        root=REPO_ROOT,
        source_file="raw/efsa-guidance/base-term-selection.md",
        page_names=["base-term-selection.md"],
    )

    with pytest.raises(SourceIntakeError) as excinfo:
        AnthropicSourceIntakeReviewer(
            client=client,
            model="fake-intake-model",
            thinking_enabled=True,
        ).run(payload)

    message = str(excinfo.value)
    assert "max_tokens" in message
    assert "--no-thinking" in message
