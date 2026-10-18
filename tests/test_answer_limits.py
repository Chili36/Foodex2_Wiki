import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from wiki_api.librarian import ANSWERER_OUTPUT_SCHEMA, AnthropicFoodEx2Answerer


ANSWER = json.dumps({"answer": "Complete answer.", "citations": ["base-term-selection.md"]})


def response(text=ANSWER, reason="end_turn", output=30):
    return {
        "stop_reason": reason,
        "content": [
            {"type": "thinking", "thinking": "", "signature": "test"},
            {"type": "text", "text": text},
        ],
        "usage": {"input_tokens": 100, "output_tokens": output},
    }


def answerer(*responses, **kwargs):
    client = SimpleNamespace(messages=SimpleNamespace(create=MagicMock(side_effect=responses)))
    return AnthropicFoodEx2Answerer(client=client, model="claude-sonnet-5-5", **kwargs), client


@pytest.mark.parametrize("partial", ["", '{"answer":"cut off', ANSWER])
def test_retry_discards_token_limited_json_and_counts_both_calls(partial):
    runner, client = answerer(response(partial, "max_tokens", 8192), response())
    result = runner.run(question="question", pages=[])
    assert result.answer == "Complete answer."
    calls = client.messages.create.call_args_list
    assert [c.kwargs["max_tokens"] for c in calls] == [8192, 16384]
    assert calls[0].kwargs["messages"] == calls[1].kwargs["messages"]
    assert result.token_summary["calls"] == 2
    assert result.token_summary["input_tokens"] == 200
    assert result.token_summary["output_tokens"] == 8222
    assert result.timing_summary["calls"] == 2


def test_second_token_limit_returns_clear_error_instead_of_parsing_partial_json():
    runner, client = answerer(response("", "max_tokens"), response(ANSWER, "max_tokens"))
    with pytest.raises(RuntimeError, match="output limit"):
        runner.run(question="question", pages=[])
    assert client.messages.create.call_count == 2


def test_explicit_budget_at_retry_ceiling_is_not_increased():
    runner, client = answerer(response("", "max_tokens"), max_tokens=16384)
    with pytest.raises(RuntimeError, match="output limit"):
        runner.run(question="question", pages=[])
    assert client.messages.create.call_count == 1
    assert client.messages.create.call_args.kwargs["max_tokens"] == 16384


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_effort_is_forwarded_alongside_json_schema_on_both_attempts(effort):
    runner, client = answerer(response("", "max_tokens"), response(), reasoning_effort=effort)
    runner.run(question="question", pages=[])
    for call in client.messages.create.call_args_list:
        assert call.kwargs["output_config"] == {
            "effort": effort,
            "format": {"type": "json_schema", "schema": ANSWERER_OUTPUT_SCHEMA},
        }


def test_default_effort_and_older_model_budget_remain_unchanged():
    runner, client = answerer(response())
    runner.run(question="question", pages=[])
    assert "effort" not in client.messages.create.call_args.kwargs["output_config"]
    older = AnthropicFoodEx2Answerer(client=client, model="claude-sonnet-4-6")
    assert older.max_tokens == 2500


def test_lmstudio_effort_still_uses_its_own_parameter():
    _, client = answerer(response())
    runner = AnthropicFoodEx2Answerer(client=client, model="lmstudio:local", reasoning_effort="low")
    runner.run(question="question", pages=[])
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["reasoning_effort"] == "low"
    assert "output_config" not in kwargs
    assert kwargs["max_tokens"] == 2500


@pytest.mark.parametrize("effort", ["low", "medium"])
def test_default_model_routes_requested_effort_to_anthropic(monkeypatch, effort):
    import wiki_api.app as app_module
    import wiki_api.librarian as librarian_module

    _, client = answerer(response())
    monkeypatch.setenv("WIKI_ANSWERER_MODEL", "claude-sonnet-5-5")
    monkeypatch.setattr(librarian_module, "build_anthropic_client", lambda: client)
    runner = app_module.get_answerer_runner(reasoning_effort=effort)
    runner.run(question="question", pages=[])
    assert client.messages.create.call_args.kwargs["model"] == "claude-sonnet-5-5"
    assert client.messages.create.call_args.kwargs["output_config"]["effort"] == effort
