from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .failure_learning import analyze_and_log_completed_run, analyze_and_log_failure
from .models import AgentResult, CodeRequest, CodeResponse, ToolCallRecord
from .prompts import (
    AGENT_MD_PATH,
    build_developer_preamble,
    build_short_instructions,
    build_user_task,
)
from .settings import APP_DIR, Settings
from .tools import FoodEx2Toolbox, build_tool_definitions
from .trace import RunLogger, compact_for_model, make_trace_record, new_run_id


class AgentRunError(RuntimeError):
    pass


SELF_EVALUATION_INSTRUCTIONS = """You are a FoodEx2 coding quality reviewer.

Review a completed FoodEx2 agent result using only the source request, final result, validator/tool evidence, and trace summary supplied to you.

Judge whether the final answer is ready to use, not whether another theoretical answer might exist.

Rules:
- Check source-fact coverage: every meaningful source phrase should be covered by the base term, an implicit facet, an explicit facet, or explicitly marked unsupported/not coded.
- If a humanReference is supplied, compare the agent code against it facet-by-facet. Treat the human code as expert evidence, not automatically correct; explain where the agent is weaker, stronger, or simply using a different valid base strategy.
- Use recentRunLearning as context for repeated behavior patterns, especially over-searching, base-only answers, missing facets, and cases where a specific base term may replace explicit characterising facets.
- Check overcoding: flag exact numeric facets used for thresholds/ranges, invented descriptors, or facets not backed by tools.
- Check undercoding: flag a source-critical detail that was ignored despite available evidence.
- Check tool discipline: note oversearching or unnecessary tool calls if visible.
- Be concise and actionable.
- Return JSON only.

Return this JSON shape:
{
  "verdict": "accept|review|revise",
  "score": 1,
  "sourceFactCoverage": [
    {"fact": "source phrase", "status": "covered_by_base|covered_by_implicit|covered_by_explicit|unsupported_not_coded|ambiguous|missed", "evidence": "short reason"}
  ],
  "humanComparison": {
    "referenceProvided": false,
    "agentCode": "code",
    "humanCode": "code or null",
    "keyDifferences": ["difference"],
    "assessment": "short comparison"
  },
  "codingRisks": ["risk or caveat"],
  "toolUseAssessment": "one sentence",
  "recommendedNextAction": "use answer|review manually|revise and rerun"
}
"""


EventSink = Callable[[dict[str, Any]], Awaitable[None] | None]


async def _emit(event_sink: EventSink | None, event: dict[str, Any]) -> None:
    if event_sink is None:
        return
    result = event_sink(event)
    if result is not None:
        await result


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise AgentRunError("Empty final response from model")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    raise AgentRunError("Could not extract JSON object from final model response")


def normalize_agent_result_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "validationCheck" not in normalized and "validation" in normalized:
        normalized["validationCheck"] = normalized["validation"]
    if "alternativeCodes" not in normalized and "alternatives" in normalized:
        normalized["alternativeCodes"] = normalized["alternatives"]
    if "explicitFacets" not in normalized:
        normalized["explicitFacets"] = []
    if "factCoverage" not in normalized:
        normalized["factCoverage"] = []
    normalized["confidence"] = _normalize_confidence(normalized.get("confidence"))
    return normalized


def _normalize_confidence(value: Any) -> int:
    if isinstance(value, bool):
        return 1
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            return 1
    if isinstance(value, int):
        return max(1, min(5, value))
    if isinstance(value, float):
        if 0.0 <= value <= 1.0:
            return max(1, min(5, round(1 + value * 4)))
        if 5.0 < value <= 100.0:
            return max(1, min(5, round(1 + (value / 100.0) * 4)))
        return max(1, min(5, round(value)))
    return 1


def _get_attr(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


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


def _function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (_get_attr(response, "output", []) or [])
        if _get_attr(item, "type") == "function_call"
    ]


def _response_usage_event(response: Any, *, source: str, model: str) -> dict[str, Any] | None:
    usage = _get_attr(response, "usage")
    if usage is None:
        return None
    input_tokens = int(
        _get_attr(usage, "input_tokens", None)
        or _get_attr(usage, "prompt_tokens", None)
        or 0
    )
    output_tokens = int(
        _get_attr(usage, "output_tokens", None)
        or _get_attr(usage, "completion_tokens", None)
        or 0
    )
    total_tokens = int(
        _get_attr(usage, "total_tokens", None)
        or _get_attr(usage, "total_tracked_tokens", None)
        or input_tokens + output_tokens
    )
    return {
        "source": source,
        "model": model,
        "calls": 1,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "total_tracked_tokens": total_tokens,
    }


def _is_hard_warning(warning: Any) -> bool:
    if not isinstance(warning, dict):
        return False
    severity = str(warning.get("severity") or warning.get("level") or "").lower()
    return severity in {"hard", "error", "critical", "high"}


def _is_clean_validation_result(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("valid") is True:
        return not result.get("hardWarnings")
    if result.get("passes") is True:
        return not any(_is_hard_warning(warning) for warning in result.get("warnings", []))
    return False


def _validation_snapshot(input_code: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": result.get("cleanedCode") or result.get("code") or input_code,
        "inputCode": input_code,
        "description": result.get("interpretedDescription")
        or result.get("description")
        or result.get("name"),
    }


def _parse_tool_arguments(call: Any) -> dict[str, Any]:
    raw_args = _get_attr(call, "arguments", "{}") or "{}"
    return json.loads(raw_args) if isinstance(raw_args, str) else raw_args


def _tool_call_snapshot(call: Any) -> dict[str, Any]:
    try:
        arguments = _parse_tool_arguments(call)
    except Exception as exc:
        arguments = {"_parse_error": str(exc), "raw": _get_attr(call, "arguments", "")}
    return {
        "name": str(_get_attr(call, "name")),
        "arguments": arguments,
        "call_id": _get_attr(call, "call_id"),
    }


def _usage_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "total_tracked_tokens": 0,
    }
    by_source: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}

    def add(target: dict[str, Any], event: dict[str, Any]) -> None:
        target["calls"] = int(target.get("calls", 0)) + int(event.get("calls") or 0)
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "total_tracked_tokens",
        ):
            target[key] = int(target.get(key, 0)) + int(event.get(key) or 0)

    for event in events:
        add(totals, event)
        source = str(event.get("source") or "unknown")
        model = str(event.get("model") or "unknown")
        by_source.setdefault(source, {"source": source, "model": model})
        by_model.setdefault(model, {"model": model})
        add(by_source[source], event)
        add(by_model[model], event)

    return {
        "totals": totals,
        "by_source": list(by_source.values()),
        "by_model": list(by_model.values()),
    }


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _trace_for_evaluation(trace: list[ToolCallRecord], settings: Settings) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in trace:
        rows.append(
            {
                "name": record.name,
                "arguments": record.arguments,
                "result": compact_for_model(record.result, settings),
                "resultCount": record.resultCount,
                "truncated": record.truncated,
                "logRef": record.logRef,
            }
        )
    return rows


def _recent_jsonl_records(path_text: str, *, limit: int = 1) -> list[dict[str, Any]]:
    path = Path(path_text)
    if not path.is_absolute():
        path = APP_DIR / path
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(records) >= limit:
            break
    return list(reversed(records))


def _preview_result(result: Any, max_items: int = 5) -> list[str]:
    if isinstance(result, dict) and result.get("blocked"):
        instruction = str(result.get("instruction") or "").replace("\n", " ").strip()
        if len(instruction) > 200:
            instruction = instruction[:199].rstrip() + "…"
        return [f"blocked: {result.get('reason')}", instruction]

    if isinstance(result, dict) and result.get("agentHint"):
        hint = str(result["agentHint"]).replace("\n", " ").strip()
        if len(hint) > 240:
            hint = hint[:239].rstrip() + "…"
        return [f"hint: {hint}"]

    if isinstance(result, dict) and result.get("answer"):
        answer = str(result["answer"]).replace("\n", " ").strip()
        if len(answer) > 240:
            answer = answer[:239].rstrip() + "…"
        return [f"answer: {answer}"]

    if isinstance(result, dict):
        for key in ("results", "terms", "items", "facets", "pages"):
            value = result.get(key)
            if isinstance(value, list):
                result = value
                break

    if not isinstance(result, list):
        return []

    preview = []
    for item in result[:max_items]:
        if isinstance(item, dict):
            code = item.get("code") or item.get("termCode") or item.get("page_name") or ""
            name = item.get("name") or item.get("termExtendedName") or item.get("title") or ""
            score = item.get("score")
            text = " ".join(str(part) for part in (code, name) if part)
            if score is not None:
                text = f"{text} ({float(score):.3f})" if text else f"score {float(score):.3f}"
            preview.append(text or json.dumps(item, ensure_ascii=False, default=str)[:120])
        else:
            preview.append(str(item)[:120])
    return preview


class FoodEx2Agent:
    def __init__(self, *, settings: Settings, toolbox: FoodEx2Toolbox, client: Any | None = None):
        self.settings = settings
        self.toolbox = toolbox
        self.client = client

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AgentRunError("openai package is not installed") from exc
        self.client = OpenAI()
        return self.client

    async def _create_response(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._client().responses.create, **kwargs)

    async def _record_failure_learning(
        self,
        *,
        request: CodeRequest,
        agent_model: str,
        run_id: str,
        run_log_file: str,
        trace: list[ToolCallRecord],
        error: str,
        logger: RunLogger,
        event_sink: EventSink | None,
    ) -> dict[str, Any]:
        await _emit(
            event_sink,
            {
                "event": "failure_analysis_start",
                "runId": run_id,
                "model": self.settings.failure_analysis_model,
            },
        )
        learning_log_file, learning_record = await analyze_and_log_failure(
            client=self._client(),
            settings=self.settings,
            run_id=run_id,
            run_log_file=run_log_file,
            request=request,
            trace=trace,
            error=error,
            agent_model=agent_model,
        )
        logger.write(
            {
                "event": "failure_analysis_written",
                "learningLogFile": str(learning_log_file),
                "model": self.settings.failure_analysis_model,
                "analysis": learning_record.get("analysis"),
                "analysisStatus": learning_record.get("status"),
            }
        )
        await _emit(
            event_sink,
            {
                "event": "failure_analysis_written",
                "runId": run_id,
                "learningLogFile": str(learning_log_file),
                "analysis": learning_record.get("analysis"),
                "analysisStatus": learning_record.get("status"),
            },
        )
        return learning_record

    async def _record_completed_run_learning(
        self,
        *,
        request: CodeRequest,
        agent_model: str,
        run_id: str,
        run_log_file: str,
        trace: list[ToolCallRecord],
        result: dict[str, Any],
        logger: RunLogger,
        event_sink: EventSink | None,
    ) -> None:
        await _emit(
            event_sink,
            {
                "event": "run_learning_start",
                "runId": run_id,
                "model": self.settings.failure_analysis_model,
            },
        )
        learning_log_file = await analyze_and_log_completed_run(
            client=self._client(),
            settings=self.settings,
            run_id=run_id,
            run_log_file=run_log_file,
            request=request,
            trace=trace,
            result=result,
            agent_model=agent_model,
        )
        logger.write(
            {
                "event": "run_learning_written",
                "learningLogFile": str(learning_log_file),
                "model": self.settings.failure_analysis_model,
            }
        )
        await _emit(
            event_sink,
            {
                "event": "run_learning_written",
                "runId": run_id,
                "learningLogFile": str(learning_log_file),
            },
        )

    async def _self_evaluate_completed_run(
        self,
        *,
        request: CodeRequest,
        model: str,
        run_id: str,
        trace: list[ToolCallRecord],
        result: dict[str, Any],
        usage_so_far: dict[str, Any],
        logger: RunLogger,
        event_sink: EventSink | None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        await _emit(event_sink, {"event": "self_evaluation_start", "model": model})
        evaluation_input = {
            "runId": run_id,
            "request": _model_dump(request),
            "humanReference": request.human_reference,
            "recentRunLearning": _recent_jsonl_records(self.settings.run_learning_log, limit=1),
            "result": result,
            "usageSoFar": usage_so_far,
            "trace": _trace_for_evaluation(trace, self.settings),
        }
        try:
            response = await self._create_response(
                model=model,
                instructions=SELF_EVALUATION_INSTRUCTIONS,
                input=json.dumps(evaluation_input, ensure_ascii=False, default=str),
            )
            usage_event = _response_usage_event(
                response,
                source="self_evaluation",
                model=model,
            )
            evaluation = extract_json_object(_output_text(response))
            record = {
                "status": "completed",
                "model": model,
                **evaluation,
            }
            logger.write({"event": "self_evaluation", "evaluation": record})
            await _emit(
                event_sink,
                {
                    "event": "self_evaluation_completed",
                    "model": model,
                    "verdict": record.get("verdict"),
                    "score": record.get("score"),
                },
            )
            return record, usage_event
        except Exception as exc:
            record = {
                "status": "failed",
                "model": model,
                "error": str(exc),
            }
            logger.write({"event": "self_evaluation_failed", "evaluation": record})
            await _emit(
                event_sink,
                {
                    "event": "self_evaluation_failed",
                    "model": model,
                    "error": str(exc),
                },
            )
            return record, None

    async def run(self, request: CodeRequest, event_sink: EventSink | None = None) -> CodeResponse:
        # Toolbox is shared across runs; clear per-request state so a prior
        # run's accepted_validation does not leak into this one as a stale
        # `validatedDraft` agentHint (see iter-1 run_learning analysis).
        self.toolbox.reset_request_state()
        trace: list[ToolCallRecord] = []
        usage_events: list[dict[str, Any]] = []
        run_id = new_run_id()
        logger = RunLogger(self.settings, run_id)
        agent_model = request.agent_model or self.settings.openai_model
        self_evaluation_model = request.self_evaluation_model or self.settings.self_evaluation_model
        max_rounds = request.max_tool_rounds or self.settings.max_tool_rounds
        user_task = build_user_task(
            request.search_term,
            language_hint=request.language_hint,
            domain=request.domain,
        )
        short_instructions = build_short_instructions()
        developer_preamble = build_developer_preamble(
            include_debug_tool_why=self.settings.tool_reason_debug
        )
        tool_definitions = build_tool_definitions(
            include_debug_why=self.settings.tool_reason_debug
        )
        accepted_validation: dict[str, Any] | None = None
        post_validation_nonvalidator_calls = 0
        request_dump = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        logger.write(
            {
                "event": "run_start",
                "model": agent_model,
                "selfEvaluationModel": self_evaluation_model,
                "agentInstructionsPath": str(AGENT_MD_PATH),
                "shortInstructionsChars": len(short_instructions),
                "developerPreambleChars": len(developer_preamble),
                "toolReasonDebug": self.settings.tool_reason_debug,
                "postValidationToolBudget": self.settings.post_validation_tool_budget,
                "request": request_dump,
            }
        )
        await _emit(
            event_sink,
            {
                "event": "run_start",
                "runId": run_id,
                "logFile": str(logger.path),
                "model": agent_model,
                "selfEvaluationModel": self_evaluation_model,
                "maxToolRounds": max_rounds,
                "agentInstructionsPath": str(AGENT_MD_PATH),
                "toolReasonDebug": self.settings.tool_reason_debug,
                "postValidationToolBudget": self.settings.post_validation_tool_budget,
            },
        )

        async def complete_response(final_response: Any) -> CodeResponse:
            final_text = _output_text(final_response)
            payload = extract_json_object(final_text)
            logger.write({"event": "final_payload_extracted", "result": payload})
            payload = normalize_agent_result_payload(payload)
            self_evaluation: dict[str, Any] | None = None
            if request.audit_mode:
                usage_before_eval = _usage_summary(usage_events)
                self_evaluation, eval_usage_event = await self._self_evaluate_completed_run(
                    request=request,
                    model=self_evaluation_model,
                    run_id=run_id,
                    trace=trace,
                    result=payload,
                    usage_so_far=usage_before_eval,
                    logger=logger,
                    event_sink=event_sink,
                )
                if eval_usage_event:
                    usage_events.append(eval_usage_event)
                    logger.write({"event": "model_usage", **eval_usage_event})
            usage = _usage_summary(usage_events)
            logger.write(
                {
                    "event": "run_completed",
                    "result": payload,
                    "selfEvaluation": self_evaluation,
                }
            )
            logger.write({"event": "usage_summary", "usage": usage})
            completed = CodeResponse(
                status="completed",
                model=agent_model,
                runId=run_id,
                logFile=str(logger.path),
                usage=usage,
                selfEvaluation=self_evaluation,
                result=AgentResult(**payload),
                trace=trace,
                raw_final=payload,
            )
            await _emit(
                event_sink,
                {"event": "completed", "response": _model_dump(completed)},
            )
            await self._record_completed_run_learning(
                request=request,
                agent_model=agent_model,
                run_id=run_id,
                run_log_file=str(logger.path),
                trace=trace,
                result=payload,
                logger=logger,
                event_sink=event_sink,
            )
            return completed

        try:
            await _emit(event_sink, {"event": "model_request", "round": 0})
            response = await self._create_response(
                model=agent_model,
                instructions=short_instructions,
                input=[
                    {"role": "developer", "content": developer_preamble},
                    {"role": "user", "content": user_task},
                ],
                tools=tool_definitions,
                parallel_tool_calls=False,
            )
            usage_event = _response_usage_event(
                response,
                source="agent.round_0",
                model=agent_model,
            )
            if usage_event:
                usage_events.append(usage_event)
                logger.write({"event": "model_usage", **usage_event})
            await _emit(
                event_sink,
                {
                    "event": "model_response",
                    "round": 0,
                    "responseId": _get_attr(response, "id"),
                    "toolCalls": len(_function_calls(response)),
                },
            )

            for _round in range(max_rounds):
                calls = _function_calls(response)
                if not calls:
                    return await complete_response(response)

                if accepted_validation is not None:
                    nonvalidator_calls = [
                        call
                        for call in calls
                        if str(_get_attr(call, "name")) != "validator_validate_code"
                    ]
                    if (
                        nonvalidator_calls
                        and post_validation_nonvalidator_calls
                        >= self.settings.post_validation_tool_budget
                    ):
                        blocked_calls = [_tool_call_snapshot(call) for call in calls]
                        logger.write(
                            {
                                "event": "post_validation_tool_calls_blocked",
                                "round": _round + 1,
                                "acceptedValidation": accepted_validation,
                                "postValidationNonvalidatorCalls": post_validation_nonvalidator_calls,
                                "blockedCalls": blocked_calls,
                            }
                        )
                        await _emit(
                            event_sink,
                            {
                                "event": "post_validation_tool_calls_blocked",
                                "round": _round + 1,
                                "acceptedCode": accepted_validation.get("code"),
                                "calls": blocked_calls,
                            },
                        )
                        blocked_outputs = [
                            {
                                "type": "function_call_output",
                                "call_id": _get_attr(call, "call_id"),
                                "output": self.toolbox.serialize_result(
                                    {
                                        "blocked": True,
                                        "reason": (
                                            "The code already validated and the "
                                            "post-validation tool budget is exhausted. "
                                            "Return final JSON now using the accepted "
                                            "validation and source-fact ledger."
                                        ),
                                        "acceptedValidation": accepted_validation,
                                    }
                                ),
                            }
                            for call in calls
                        ]
                        await _emit(
                            event_sink,
                            {"event": "model_request", "round": _round + 1, "finalize": True},
                        )
                        response = await self._create_response(
                            model=agent_model,
                            previous_response_id=_get_attr(response, "id"),
                            input=blocked_outputs,
                            tools=[],
                            parallel_tool_calls=False,
                        )
                        usage_event = _response_usage_event(
                            response,
                            source=f"agent.round_{_round + 1}.forced_final",
                            model=agent_model,
                        )
                        if usage_event:
                            usage_events.append(usage_event)
                            logger.write({"event": "model_usage", **usage_event})
                        await _emit(
                            event_sink,
                            {
                                "event": "model_response",
                                "round": _round + 1,
                                "responseId": _get_attr(response, "id"),
                                "toolCalls": len(_function_calls(response)),
                                "finalize": True,
                            },
                        )
                        if not _function_calls(response):
                            return await complete_response(response)
                        continue

                tool_outputs: list[dict[str, Any]] = []
                for call in calls:
                    name = str(_get_attr(call, "name"))
                    arguments = _parse_tool_arguments(call)
                    log_ref = f"{run_id}:{len(trace) + 1}"
                    if accepted_validation is not None and name != "validator_validate_code":
                        post_validation_nonvalidator_calls += 1
                        diagnostic = {
                            "event": "post_validation_tool_call",
                            "ref": log_ref,
                            "round": _round + 1,
                            "name": name,
                            "arguments": arguments,
                            "acceptedValidation": accepted_validation,
                        }
                        logger.write(diagnostic)
                        await _emit(
                            event_sink,
                            {
                                "event": "post_validation_tool_call",
                                "round": _round + 1,
                                "ref": log_ref,
                                "name": name,
                                "arguments": arguments,
                                "acceptedCode": accepted_validation.get("code"),
                            },
                        )
                    await _emit(
                        event_sink,
                        {
                            "event": "tool_call_start",
                            "round": _round + 1,
                            "ref": log_ref,
                            "name": name,
                            "arguments": arguments,
                        },
                    )
                    raw_result = await self.toolbox.execute(name, arguments)
                    if name == "validator_validate_code" and _is_clean_validation_result(raw_result):
                        accepted_validation = _validation_snapshot(
                            str(arguments.get("code") or ""),
                            raw_result,
                        )
                    for usage_event in self.toolbox.pop_usage_events():
                        usage_events.append(usage_event)
                        logger.write({"event": "tool_usage", **usage_event})
                    logger.write(
                        {
                            "event": "tool_call",
                            "ref": log_ref,
                            "round": _round + 1,
                            "name": name,
                            "arguments": arguments,
                            "result": raw_result,
                        }
                    )
                    record = make_trace_record(
                        name=name,
                        arguments=arguments,
                        result=raw_result,
                        settings=self.settings,
                        log_ref=log_ref,
                    )
                    trace.append(record)
                    await _emit(
                        event_sink,
                        {
                            "event": "tool_call_result",
                            "round": _round + 1,
                            "ref": log_ref,
                            "name": name,
                            "resultCount": record.resultCount,
                            "truncated": record.truncated,
                            "preview": _preview_result(raw_result),
                        },
                    )
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": _get_attr(call, "call_id"),
                            "output": self.toolbox.serialize_result(
                                compact_for_model(raw_result, self.settings)
                            ),
                        }
                    )

                await _emit(event_sink, {"event": "model_request", "round": _round + 1})
                response = await self._create_response(
                    model=agent_model,
                    previous_response_id=_get_attr(response, "id"),
                    input=tool_outputs,
                    tools=tool_definitions,
                    parallel_tool_calls=False,
                )
                usage_event = _response_usage_event(
                    response,
                    source=f"agent.round_{_round + 1}",
                    model=agent_model,
                )
                if usage_event:
                    usage_events.append(usage_event)
                    logger.write({"event": "model_usage", **usage_event})
                await _emit(
                    event_sink,
                    {
                        "event": "model_response",
                        "round": _round + 1,
                        "responseId": _get_attr(response, "id"),
                        "toolCalls": len(_function_calls(response)),
                    },
                )

            error = f"Exceeded max tool rounds ({max_rounds})"
            pending_tool_calls = [_tool_call_snapshot(call) for call in _function_calls(response)]
            if pending_tool_calls:
                logger.write(
                    {
                        "event": "pending_tool_calls_at_max_rounds",
                        "calls": pending_tool_calls,
                    }
                )
                await _emit(
                    event_sink,
                    {"event": "pending_tool_calls", "calls": pending_tool_calls},
                )
            usage = _usage_summary(usage_events)
            logger.write({"event": "usage_summary", "usage": usage})
            failure_record = await self._record_failure_learning(
                request=request,
                agent_model=agent_model,
                run_id=run_id,
                run_log_file=str(logger.path),
                trace=trace,
                error=error,
                logger=logger,
                event_sink=event_sink,
            )
            failed = CodeResponse(
                status="failed",
                model=agent_model,
                runId=run_id,
                logFile=str(logger.path),
                usage=usage,
                failureAnalysis=failure_record,
                trace=trace,
                error=error,
            )
            await _emit(event_sink, {"event": "failed", "response": _model_dump(failed)})
            return failed
        except Exception as exc:
            error = str(exc)
            logger.write({"event": "run_error", "error": error})
            usage = _usage_summary(usage_events)
            logger.write({"event": "usage_summary", "usage": usage})
            failure_record = await self._record_failure_learning(
                request=request,
                agent_model=agent_model,
                run_id=run_id,
                run_log_file=str(logger.path),
                trace=trace,
                error=error,
                logger=logger,
                event_sink=event_sink,
            )
            failed = CodeResponse(
                status="failed",
                model=agent_model,
                runId=run_id,
                logFile=str(logger.path),
                usage=usage,
                failureAnalysis=failure_record,
                trace=trace,
                error=error,
            )
            await _emit(event_sink, {"event": "failed", "response": _model_dump(failed)})
            return failed
