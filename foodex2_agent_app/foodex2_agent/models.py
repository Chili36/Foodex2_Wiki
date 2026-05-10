from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CodeRequest(BaseModel):
    search_term: str
    language_hint: str | None = None
    domain: str | None = None
    human_reference: str | None = None
    agent_model: str | None = None
    self_evaluation_model: str | None = None
    max_tool_rounds: int | None = Field(default=None, ge=1, le=30)
    audit_mode: bool = True


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: Any
    resultCount: int | None = None
    truncated: bool = False
    logRef: str | None = None


class AgentResult(BaseModel):
    selectedCode: str
    selectedName: str
    selectedTermType: str
    constructedCode: str
    reasoning: str
    implicitFacets: list[Any] = Field(default_factory=list)
    explicitFacets: list[Any] = Field(default_factory=list)
    suggestedExplicitFacets: list[Any] = Field(default_factory=list)
    factCoverage: list[dict[str, Any]] = Field(default_factory=list)
    validationCheck: dict[str, Any] = Field(default_factory=dict)
    alternativeCodes: list[dict[str, Any]] = Field(default_factory=list)
    confidence: int = Field(ge=1, le=5)


class CodeResponse(BaseModel):
    status: Literal["completed", "failed"]
    model: str
    runId: str | None = None
    logFile: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    selfEvaluation: dict[str, Any] | None = None
    failureAnalysis: dict[str, Any] | None = None
    result: AgentResult | None = None
    trace: list[ToolCallRecord] = Field(default_factory=list)
    raw_final: Any | None = None
    error: str | None = None
