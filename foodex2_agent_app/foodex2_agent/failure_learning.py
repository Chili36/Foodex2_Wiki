from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CodeRequest, ToolCallRecord
from .settings import APP_DIR, Settings


FAILURE_ANALYSIS_INSTRUCTIONS = """You are a senior FoodEx2 agent-debugging reviewer.

Analyze a failed FoodEx2 coding-agent run and produce reusable learning for improving the agent.

Rules:
- Be concrete and evidence-based. Cite tool call names, repeated behavior, missing information, or bad sequencing.
- Separate root cause from symptoms.
- Prefer actionable changes to prompts, tools, retrieval policy, validation flow, or UI/logging.
- Do not solve the original FoodEx2 coding task unless it directly explains the failure.
- Return JSON only.

Return this JSON shape:
{
  "failureType": "tool_loop|bad_retrieval|missing_tool|bad_prompt|validator_issue|model_output|infrastructure|unknown",
  "rootCause": "one concise paragraph",
  "evidence": ["specific observed fact", "specific observed fact"],
  "learning": ["reusable lesson for future runs"],
  "recommendedChanges": ["specific engineering or prompt change"],
  "nextTest": "one targeted test case or regression check",
  "severity": "low|medium|high"
}
"""

SUCCESS_ANALYSIS_INSTRUCTIONS = """You are a senior FoodEx2 coding-agent reviewer.

Analyze a completed FoodEx2 coding-agent run and produce reusable learning for improving the agent.

Rules:
- Be concrete and evidence-based. Cite tool call names, validation facts, useful sequence choices, and wasted steps.
- Identify what worked, what should be repeated, and what should be made more efficient.
- If the final code looks weak or overconfident from the trace, say so as residual risk rather than inventing new facts.
- Prefer actionable changes to prompts, tools, retrieval policy, validation flow, or UI/logging.
- Return JSON only.

Return this JSON shape:
{
  "outcomeType": "good_pattern|acceptable_with_risk|inefficient_success|questionable_success",
  "whatWorked": ["specific reusable pattern"],
  "wasteOrRisk": ["specific inefficiency or residual risk"],
  "learning": ["reusable lesson for future runs"],
  "recommendedChanges": ["specific engineering or prompt change"],
  "nextTest": "one targeted regression or evaluation case",
  "severity": "low|medium|high"
}
"""


def _output_text(response: Any) -> str:
    direct = _get_attr(response, "output_text")
    if direct:
        return str(direct)
    chunks: list[str] = []
    for item in _get_attr(response, "output", []) or []:
        if _get_attr(item, "type") == "message":
            for content in _get_attr(item, "content", []) or []:
                if _get_attr(content, "type") in {"output_text", "text"}:
                    chunks.append(str(_get_attr(content, "text", "")))
    return "".join(chunks).strip()


def _get_attr(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("Empty failure-analysis response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not extract JSON object from failure-analysis response")


def _path_from_setting(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = APP_DIR / path
    return path


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _trace_payload(trace: list[ToolCallRecord]) -> list[dict[str, Any]]:
    return [_model_dump(record) for record in trace]


def append_learning_record(settings: Settings, record: dict[str, Any], *, log_path: str) -> Path:
    path = _path_from_setting(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


async def analyze_and_log_failure(
    *,
    client: Any,
    settings: Settings,
    run_id: str,
    run_log_file: str,
    request: CodeRequest,
    trace: list[ToolCallRecord],
    error: str,
    agent_model: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    base_record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "runId": run_id,
        "runLogFile": run_log_file,
        "agentModel": agent_model or settings.openai_model,
        "analysisModel": settings.failure_analysis_model,
        "request": _model_dump(request),
        "error": error,
        "toolCallCount": len(trace),
    }
    analysis_input = {
        **base_record,
        "trace": _trace_payload(trace),
    }

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model=settings.failure_analysis_model,
            instructions=FAILURE_ANALYSIS_INSTRUCTIONS,
            input=json.dumps(analysis_input, ensure_ascii=False, default=str),
        )
        analysis = _extract_json_object(_output_text(response))
        record = {
            **base_record,
            "status": "analyzed",
            "analysis": analysis,
        }
    except Exception as exc:
        record = {
            **base_record,
            "status": "analysis_failed",
            "analysisError": str(exc),
        }

    path = append_learning_record(settings, record, log_path=settings.failure_learning_log)
    return path, record


async def analyze_and_log_completed_run(
    *,
    client: Any,
    settings: Settings,
    run_id: str,
    run_log_file: str,
    request: CodeRequest,
    trace: list[ToolCallRecord],
    result: dict[str, Any],
    agent_model: str | None = None,
) -> Path:
    base_record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "runId": run_id,
        "runLogFile": run_log_file,
        "agentModel": agent_model or settings.openai_model,
        "analysisModel": settings.failure_analysis_model,
        "request": _model_dump(request),
        "result": result,
        "toolCallCount": len(trace),
    }
    analysis_input = {
        **base_record,
        "trace": _trace_payload(trace),
    }

    try:
        response = await asyncio.to_thread(
            client.responses.create,
            model=settings.failure_analysis_model,
            instructions=SUCCESS_ANALYSIS_INSTRUCTIONS,
            input=json.dumps(analysis_input, ensure_ascii=False, default=str),
        )
        analysis = _extract_json_object(_output_text(response))
        record = {
            **base_record,
            "runStatus": "completed",
            "status": "analyzed",
            "analysis": analysis,
        }
    except Exception as exc:
        record = {
            **base_record,
            "runStatus": "completed",
            "status": "analysis_failed",
            "analysisError": str(exc),
        }

    return append_learning_record(settings, record, log_path=settings.run_learning_log)
