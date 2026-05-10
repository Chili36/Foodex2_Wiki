from __future__ import annotations

import asyncio
import json
from pathlib import Path

from foodex2_agent.agent import FoodEx2Agent, extract_json_object, normalize_agent_result_payload
from foodex2_agent.models import CodeRequest, ToolCallRecord
from foodex2_agent.planning import plan_source_text
from foodex2_agent.prompts import build_agent_instructions
from foodex2_agent.settings import Settings
from foodex2_agent.trace import compact_value
from foodex2_agent.tools import FoodEx2Toolbox, TOOL_DEFINITIONS, build_tool_definitions


class FakeCatalog:
    async def search_terms(self, **kwargs):
        return {"terms": [{"code": "A02QF", "name": "Fresh uncured cheese", "termType": "d"}]}

    async def get_term(self, code):
        return {"code": code, "name": "Fresh uncured cheese", "termType": "d"}

    async def get_parents(self, code):
        return {"code": code, "parents": []}

    async def get_children(self, code, limit=50):
        return {"code": code, "children": [], "limit": limit}

    async def get_implicit_facets(self, code):
        return {"code": code, "implicitFacets": []}

    async def search_facets(self, **kwargs):
        return {"facets": [{"code": "A073H", "facetType": "F10", "name": "20 % fat"}]}


class FakeSemantic:
    async def search_candidates(self, **kwargs):
        return {
            "results": [
                {
                    "score": 0.6,
                    "code": "A02QF",
                    "name": "Fresh uncured cheese",
                    "termType": "d",
                    "source": "qdrant",
                }
            ]
        }


class FakeWiki:
    async def ask(self, **kwargs):
        return {
            "answer": "Classify as derivative, find the fresh cheese base, then consider only non-implicit exact facets.",
            "citations": ["base-term-selection.md"],
            "pages_used": ["base-term-selection.md"],
            "trace": {
                "selection_method": "service-owned llm page selector + answerer",
                "retrieval": {
                    "token_summary": {
                        "model": "fake-wiki",
                        "calls": 1,
                        "input_tokens": 10,
                        "output_tokens": 3,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 13,
                    }
                },
                "answerer": {
                    "token_summary": {
                        "model": "fake-wiki",
                        "calls": 1,
                        "input_tokens": 20,
                        "output_tokens": 7,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "total_tracked_tokens": 27,
                    }
                },
            },
        }

    async def context_pack(self, **kwargs):
        return {"pages_used": ["RUNTIME_RULES.md"], "pages": []}

    async def policy_pack(self, **kwargs):
        return {
            "query_classification": {"food_type": "derivative", "domain": "all"},
            "candidate_focus": {"promising_codes": ["A02QF"], "rejected_patterns": []},
            "policy_pack": {
                "base_term_rules": ["Use a derivative cheese base."],
                "facet_rules": ["Do not duplicate implicit cheesemaking facets."],
            },
        }

    async def read_page(self, page_name):
        return {"page_name": page_name, "content": "rules"}


class FakeValidator:
    async def validate_code(self, **kwargs):
        return {"passes": True, "warnings": [], "code": kwargs["code"]}


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "FoodEx2 coding quality reviewer" in str(kwargs.get("instructions", "")):
            return {
                "usage": {
                    "input_tokens": 30,
                    "output_tokens": 10,
                    "total_tokens": 40,
                },
                "output_text": json.dumps(
                    {
                        "verdict": "accept",
                        "score": 5,
                        "sourceFactCoverage": [
                            {
                                "fact": "fresh cheese",
                                "status": "covered_by_base",
                                "evidence": "A02QF is the selected base.",
                            }
                        ],
                        "humanComparison": {
                            "referenceProvided": True,
                            "agentCode": "A02QF",
                            "humanCode": "A02QF",
                            "keyDifferences": [],
                            "assessment": "The agent matches the supplied reference.",
                        },
                        "codingRisks": [],
                        "toolUseAssessment": "Tool use was minimal.",
                        "recommendedNextAction": "use answer",
                    }
                ),
            }
        if "tools" not in kwargs:
            return {
                "output_text": json.dumps(
                    {
                        "failureType": "tool_loop",
                        "rootCause": "The model kept requesting tools and never produced a final answer.",
                        "evidence": ["The run exceeded the configured max tool rounds."],
                        "learning": ["Stop after a valid base code has been validated."],
                        "recommendedChanges": ["Add a regression for max-round failures."],
                        "nextTest": "Run the fresh cheese case with max_tool_rounds=1.",
                        "severity": "medium",
                    }
                )
            }
        return {
            "id": f"response-{len(self.calls)}",
            "output": [
                {
                    "type": "function_call",
                    "call_id": f"call-{len(self.calls)}",
                    "name": "plan_foodex2_coding_strategy",
                    "arguments": json.dumps({"source_text": "Fresh cheese"}),
                }
            ],
        }


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


class FakeCompletedResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "FoodEx2 coding quality reviewer" in str(kwargs.get("instructions", "")):
            return {
                "usage": {
                    "input_tokens": 30,
                    "output_tokens": 10,
                    "total_tokens": 40,
                },
                "output_text": json.dumps(
                    {
                        "verdict": "accept",
                        "score": 5,
                        "sourceFactCoverage": [
                            {
                                "fact": "fresh cheese",
                                "status": "covered_by_base",
                                "evidence": "A02QF is the selected base.",
                            }
                        ],
                        "humanComparison": {
                            "referenceProvided": True,
                            "agentCode": "A02QF",
                            "humanCode": "A02QF",
                            "keyDifferences": [],
                            "assessment": "The agent matches the supplied reference.",
                        },
                        "codingRisks": [],
                        "toolUseAssessment": "Tool use was minimal.",
                        "recommendedNextAction": "use answer",
                    }
                ),
            }
        if "tools" not in kwargs:
            return {
                "output_text": json.dumps(
                    {
                        "outcomeType": "good_pattern",
                        "whatWorked": ["The run produced a final validated base code."],
                        "wasteOrRisk": ["No residual risk identified in this fixture."],
                        "learning": ["Completed runs should become regression examples."],
                        "recommendedChanges": ["Keep logging success learning."],
                        "nextTest": "Repeat this fixture and assert a completed learning record exists.",
                        "severity": "low",
                    }
                )
            }
        return {
            "id": "completed-response",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 25,
                "total_tokens": 125,
            },
            "output_text": json.dumps(
                {
                    "selectedCode": "A02QF",
                    "selectedName": "Fresh uncured cheese",
                    "selectedTermType": "d",
                    "constructedCode": "A02QF",
                    "reasoning": "The base code was validated.",
                    "implicitFacets": [],
                    "suggestedExplicitFacets": [],
                    "validationCheck": {"passes": True, "warnings": []},
                    "alternativeCodes": [],
                    "confidence": 0.9,
                }
            ),
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "selectedCode": "A02QF",
                                    "selectedName": "Fresh uncured cheese",
                                    "selectedTermType": "d",
                                    "constructedCode": "A02QF",
                                    "reasoning": "The base code was validated.",
                                    "implicitFacets": [],
                                    "suggestedExplicitFacets": [],
                                    "validationCheck": {"passes": True, "warnings": []},
                                    "alternativeCodes": [],
                                    "confidence": 0.9,
                                }
                            ),
                        }
                    ],
                }
            ],
        }


class FakeCompletedOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeCompletedResponses()


class FakePostValidationResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if "tools" not in kwargs:
            return {
                "output_text": json.dumps(
                    {
                        "outcomeType": "diagnostic_fixture",
                        "whatWorked": ["The run logged a post-validation tool call."],
                        "wasteOrRisk": [],
                        "learning": [],
                        "recommendedChanges": [],
                        "nextTest": "Keep logging post-validation tool calls.",
                        "severity": "low",
                    }
                )
            }

        tool_round = sum(1 for call in self.calls if call.get("tools"))
        if tool_round == 1:
            return {
                "id": "post-validation-1",
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "validate-1",
                        "name": "validator_validate_code",
                        "arguments": json.dumps(
                            {
                                "code": "A02QF",
                                "domain": None,
                                "context": {"validatorContext": None},
                            }
                        ),
                    }
                ],
            }
        if tool_round == 2:
            return {
                "id": "post-validation-2",
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "inspect-after-valid",
                        "name": "catalog_get_term",
                        "arguments": json.dumps({"code": "A02QF"}),
                    }
                ],
            }
        return {
            "id": "post-validation-final",
            "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            "output_text": json.dumps(
                {
                    "selectedCode": "A02QF",
                    "selectedName": "Fresh uncured cheese",
                    "selectedTermType": "d",
                    "constructedCode": "A02QF",
                    "reasoning": "Validated, then one unnecessary inspection was logged.",
                    "implicitFacets": [],
                    "explicitFacets": [],
                    "suggestedExplicitFacets": [],
                    "factCoverage": [],
                    "validationCheck": {"passes": True, "warnings": []},
                    "alternativeCodes": [],
                    "confidence": 4,
                }
            ),
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "selectedCode": "A02QF",
                                    "selectedName": "Fresh uncured cheese",
                                    "selectedTermType": "d",
                                    "constructedCode": "A02QF",
                                    "reasoning": "Validated, then one unnecessary inspection was logged.",
                                    "implicitFacets": [],
                                    "explicitFacets": [],
                                    "suggestedExplicitFacets": [],
                                    "factCoverage": [],
                                    "validationCheck": {"passes": True, "warnings": []},
                                    "alternativeCodes": [],
                                    "confidence": 4,
                                }
                            ),
                        }
                    ],
                }
            ],
        }


class FakePostValidationOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakePostValidationResponses()


class FakePostValidationLoopResponses:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("tools") == []:
            return {
                "id": "forced-final",
                "usage": {"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
                "output_text": json.dumps(
                    {
                        "selectedCode": "A00ZJ",
                        "selectedName": "Pickled / marinated vegetables",
                        "selectedTermType": "d",
                        "constructedCode": "A00ZJ#F27.A00HC",
                        "reasoning": "The full code validated and further retrieval was blocked.",
                        "implicitFacets": [],
                        "explicitFacets": ["F27.A00HC"],
                        "suggestedExplicitFacets": [],
                        "factCoverage": [
                            {
                                "fact": "onion",
                                "disposition": "explicit_facet",
                                "evidence": "F27.A00HC validated.",
                            }
                        ],
                        "validationCheck": {"passes": True, "warnings": []},
                        "alternativeCodes": [],
                        "confidence": 4,
                    }
                ),
            }
        if "tools" not in kwargs:
            return {
                "output_text": json.dumps(
                    {
                        "outcomeType": "diagnostic_fixture",
                        "whatWorked": ["Forced finalization completed."],
                        "wasteOrRisk": [],
                        "learning": [],
                        "recommendedChanges": [],
                        "nextTest": "Keep forced finalization behavior.",
                        "severity": "low",
                    }
                )
            }

        tool_round = sum(1 for call in self.calls if call.get("tools") not in (None, []))
        calls_by_round = {
            1: (
                "validate-base",
                "validator_validate_code",
                {"code": "A00ZJ", "domain": None, "context": {"validatorContext": None}},
            ),
            2: ("inspect-onion", "catalog_get_term", {"code": "A00HC"}),
            3: (
                "validate-full",
                "validator_validate_code",
                {"code": "A00ZJ#F27.A00HC", "domain": None, "context": {"validatorContext": None}},
            ),
            4: ("redundant-inspect", "catalog_get_implicit_facets", {"code": "A00ZJ"}),
        }
        call_id, name, arguments = calls_by_round[tool_round]
        return {
            "id": f"loop-{tool_round}",
            "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            "output": [
                {
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": json.dumps(arguments),
                }
            ],
        }


class FakePostValidationLoopOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakePostValidationLoopResponses()


def test_toolbox_dispatches_catalog_search_terms():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call(
            "catalog_search_terms",
            {"query": "fresh cheese", "term_types": ["d"], "domain": None, "limit": 10},
        )
    )

    assert isinstance(record, ToolCallRecord)
    assert record.name == "catalog_search_terms"
    assert record.result["terms"][0]["code"] == "A02QF"


def test_toolbox_dispatches_validator():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call(
            "validator_validate_code",
            {"code": "A02QF", "domain": None, "context": {"validatorContext": None}},
        )
    )

    assert record.result["passes"] is True
    assert record.result["warnings"] == []
    assert record.result["code"] == "A02QF"
    assert "agentHint" in record.result


def test_toolbox_warns_on_repeated_search_after_accepted_validation():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )

    first = asyncio.run(
        toolbox.execute(
            "validator_validate_code",
            {"code": "A02YM", "domain": None, "context": {"validatorContext": None}},
        )
    )
    second = asyncio.run(
        toolbox.execute(
            "catalog_search_terms",
            {"query": "raw milk", "term_types": [], "domain": None, "limit": 10},
        )
    )
    third = asyncio.run(
        toolbox.execute(
            "catalog_search_terms",
            {"query": "unpasteurised milk", "term_types": [], "domain": None, "limit": 10},
        )
    )

    assert first["passes"] is True
    assert second["terms"][0]["code"] == "A02QF"
    assert "agentHint" in second
    assert "agentHint" in third
    assert third["postValidationSearchCount"] == 2
    assert third["validatedDraft"]["code"] == "A02YM"


def test_toolbox_dispatches_semantic_search():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call("semantic_search_candidates", {"query": "fresh cheese", "limit": 10})
    )

    assert record.result["results"][0]["code"] == "A02QF"


def test_toolbox_dispatches_strategy_plan():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call(
            "plan_foodex2_coding_strategy",
            {
                "source_text": "Fresh cheese made from milk, using rennet and rennet substitute, with a minimum of 20% fat content."
            },
        )
    )

    assert record.result["foodTypeHypothesis"] == "derivative"
    assert record.result["baseConceptQuery"] == "fresh uncured cheese"
    assert "20 % fat" in record.result["targetedFacetQueries"]
    assert record.result["probablyImplicitOrNonCoding"]


def test_toolbox_dispatches_wiki_ask_guidance():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call(
            "wiki_ask_guidance",
            {
                "question": "What should I think about when coding fresh cheese?",
            },
        )
    )

    assert "fresh cheese base" in record.result["answer"]
    assert "pages" not in record.result
    assert "citations" not in record.result
    assert "pages_used" not in record.result


def test_toolbox_captures_wiki_ask_usage_side_channel():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    result = asyncio.run(
        toolbox.execute(
            "wiki_ask_guidance",
            {"question": "What should I think about when coding fresh cheese?"},
        )
    )
    usage_events = toolbox.pop_usage_events()

    assert "answer" in result
    assert sum(event["total_tracked_tokens"] for event in usage_events) == 40
    assert {event["source"] for event in usage_events} == {
        "wiki_ask_guidance.retrieval",
        "wiki_ask_guidance.answerer",
    }


def test_toolbox_dispatches_wiki_policy_pack():
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    record = asyncio.run(
        toolbox.call(
            "wiki_policy_pack",
            {
                "search_term": "fresh cheese",
                "candidates_trimmed": [
                    {
                        "code": "A02QF",
                        "name": "Fresh uncured cheese",
                        "termType": "d",
                        "coverageText": "fresh cheese",
                        "implicitFacets": [],
                    }
                ],
                "domain": None,
                "max_pages": 5,
            },
        )
    )

    assert record.result["candidate_focus"]["promising_codes"] == ["A02QF"]


def test_extract_json_object_accepts_fenced_json():
    payload = extract_json_object(
        '```json\n{"selectedCode":"A02QF","confidence":4}\n```'
    )

    assert payload["selectedCode"] == "A02QF"
    assert payload["confidence"] == 4


def test_normalize_agent_result_payload_converts_confidence_to_integer_scale():
    assert normalize_agent_result_payload({"confidence": 0.9})["confidence"] == 5
    assert normalize_agent_result_payload({"confidence": 0.5})["confidence"] == 3
    assert normalize_agent_result_payload({"confidence": "4"})["confidence"] == 4
    assert normalize_agent_result_payload({"confidence": 90})["confidence"] == 5
    assert normalize_agent_result_payload({"confidence": 9})["confidence"] == 5


def test_normalize_agent_result_payload_accepts_fact_ledger_aliases():
    normalized = normalize_agent_result_payload(
        {
            "confidence": 4,
            "validation": {"passes": True, "warnings": []},
            "alternatives": [{"code": "A02LT", "reason": "raw milk, not cheese"}],
            "factCoverage": [
                {
                    "fact": "fresh cheese",
                    "disposition": "implicit_in_base",
                    "evidence": "base term scope",
                }
            ],
        }
    )

    assert normalized["validationCheck"]["passes"] is True
    assert normalized["alternativeCodes"][0]["code"] == "A02LT"
    assert normalized["explicitFacets"] == []
    assert normalized["factCoverage"][0]["disposition"] == "implicit_in_base"


def test_tool_definitions_include_required_tools():
    names = {tool["name"] for tool in TOOL_DEFINITIONS}

    assert "plan_foodex2_coding_strategy" in names
    assert "wiki_ask_guidance" in names
    assert "catalog_search_terms" in names
    assert "semantic_search_candidates" in names
    assert "wiki_context" in names
    assert "wiki_policy_pack" in names
    assert "validator_validate_code" in names


def test_base_tool_definitions_do_not_include_debug_why_by_default():
    for tool in TOOL_DEFINITIONS:
        parameters = tool["parameters"]
        assert "why" not in parameters["properties"]
        assert "why" not in parameters["required"]


def test_debug_tool_definitions_can_require_compact_why():
    debug_tools = build_tool_definitions(include_debug_why=True)

    for tool in debug_tools:
        parameters = tool["parameters"]
        assert parameters["properties"]["why"]["type"] == "string"
        assert "why" in parameters["required"]


def test_tool_definitions_are_strict_openai_schemas():
    for tool in TOOL_DEFINITIONS:
        assert tool["strict"] is True
        _assert_strict_schema(tool["parameters"], path=tool["name"])


def test_agent_instructions_are_loaded_from_markdown():
    instructions = build_agent_instructions()

    assert "# FoodEx2 Coding Agent" in instructions
    assert "Facet Construction Protocol" in instructions
    assert "Runtime Tool And Output Contract" in instructions


def test_compact_value_truncates_large_catalog_results():
    result = [
        {"code": f"A{i:04d}", "name": "x" * 1000, "type": "d", "unused": "drop"}
        for i in range(20)
    ]

    compact, truncated, count = compact_value(result, max_items=3, max_chars=50)

    assert truncated is True
    assert count == 20
    assert len(compact) == 4
    assert compact[0]["code"] == "A0000"
    assert compact[0]["name"].endswith("…")
    assert compact[-1] == {"_truncated": "17 more item(s) omitted"}


def test_strategy_plan_is_mission_first_for_cheese_case():
    plan = plan_source_text(
        "Fresh cheese made from milk, using rennet and rennet substitute, with a minimum of 20% fat content."
    )

    assert plan["foodTypeHypothesis"] == "derivative"
    assert plan["baseConceptQuery"] == "fresh uncured cheese"
    assert any("cheesemaking" in item for item in plan["probablyImplicitOrNonCoding"])
    assert plan["toolStrategy"][0]["phase"] == "1 orient"
    assert plan["searchBudget"]["semanticCandidateSearches"] == 1
    assert any("could change the constructed code" in item for item in plan["decisionChecklist"])


def test_failed_agent_run_writes_learning_log(tmp_path):
    client = FakeOpenAIClient()
    settings = Settings(
        openai_model="fake-agent",
        failure_analysis_model="fake-smart-model",
        max_tool_rounds=1,
        run_log_dir=str(tmp_path / "runs"),
        failure_learning_log=str(tmp_path / "learning" / "failure_learning.jsonl"),
    )
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    agent = FoodEx2Agent(settings=settings, toolbox=toolbox, client=client)

    response = asyncio.run(
        agent.run(CodeRequest(search_term="Fresh cheese", max_tool_rounds=1))
    )

    assert response.status == "failed"
    assert response.failureAnalysis is not None
    assert response.failureAnalysis["status"] == "analyzed"
    assert response.failureAnalysis["analysis"]["failureType"] == "tool_loop"
    learning_path = tmp_path / "learning" / "failure_learning.jsonl"
    records = [json.loads(line) for line in learning_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == "analyzed"
    assert records[0]["analysisModel"] == "fake-smart-model"
    assert records[0]["analysis"]["failureType"] == "tool_loop"
    assert records[0]["toolCallCount"] == 1
    assert any(call["model"] == "fake-smart-model" for call in client.responses.calls)
    run_records = [
        json.loads(line)
        for line in Path(response.logFile).read_text(encoding="utf-8").splitlines()
    ]
    pending = [record for record in run_records if record["event"] == "pending_tool_calls_at_max_rounds"]
    assert pending
    assert pending[0]["calls"][0]["name"] == "plan_foodex2_coding_strategy"


def test_post_validation_tool_calls_are_logged(tmp_path):
    client = FakePostValidationOpenAIClient()
    settings = Settings(
        openai_model="fake-agent",
        failure_analysis_model="fake-smart-model",
        max_tool_rounds=3,
        run_log_dir=str(tmp_path / "runs"),
        run_learning_log=str(tmp_path / "learning" / "run_learning.jsonl"),
    )
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    agent = FoodEx2Agent(settings=settings, toolbox=toolbox, client=client)

    response = asyncio.run(
        agent.run(CodeRequest(search_term="Fresh cheese", audit_mode=False))
    )

    assert response.status == "completed"
    run_records = [
        json.loads(line)
        for line in Path(response.logFile).read_text(encoding="utf-8").splitlines()
    ]
    post_validation = [
        record for record in run_records if record["event"] == "post_validation_tool_call"
    ]
    assert post_validation
    assert post_validation[0]["name"] == "catalog_get_term"
    assert post_validation[0]["acceptedValidation"]["code"] == "A02QF"


def test_post_validation_budget_blocks_extra_retrieval_and_forces_final(tmp_path):
    client = FakePostValidationLoopOpenAIClient()
    settings = Settings(
        openai_model="fake-agent",
        failure_analysis_model="fake-smart-model",
        max_tool_rounds=6,
        post_validation_tool_budget=1,
        run_log_dir=str(tmp_path / "runs"),
        run_learning_log=str(tmp_path / "learning" / "run_learning.jsonl"),
    )
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    agent = FoodEx2Agent(settings=settings, toolbox=toolbox, client=client)

    response = asyncio.run(
        agent.run(CodeRequest(search_term="Pickled onion", audit_mode=False))
    )

    assert response.status == "completed"
    assert response.result is not None
    assert response.result.constructedCode == "A00ZJ#F27.A00HC"
    assert all(record.name != "catalog_get_implicit_facets" for record in response.trace)
    run_records = [
        json.loads(line)
        for line in Path(response.logFile).read_text(encoding="utf-8").splitlines()
    ]
    blocked = [
        record for record in run_records if record["event"] == "post_validation_tool_calls_blocked"
    ]
    assert blocked
    assert blocked[0]["blockedCalls"][0]["name"] == "catalog_get_implicit_facets"
    forced_call = next(call for call in client.responses.calls if call.get("tools") == [])
    assert "blocked" in forced_call["input"][0]["output"]


def test_completed_agent_run_writes_run_learning_log(tmp_path):
    client = FakeCompletedOpenAIClient()
    settings = Settings(
        openai_model="fake-agent",
        self_evaluation_model="fake-mini",
        failure_analysis_model="fake-smart-model",
        max_tool_rounds=3,
        run_log_dir=str(tmp_path / "runs"),
        run_learning_log=str(tmp_path / "learning" / "run_learning.jsonl"),
    )
    toolbox = FoodEx2Toolbox(
        catalog=FakeCatalog(),
        semantic=FakeSemantic(),
        wiki=FakeWiki(),
        validator=FakeValidator(),
    )
    agent = FoodEx2Agent(settings=settings, toolbox=toolbox, client=client)

    response = asyncio.run(
        agent.run(
            CodeRequest(
                search_term="Fresh cheese",
                human_reference="A02QF - Fresh uncured cheese",
                agent_model="fake-cheap-agent",
                self_evaluation_model="fake-mini",
            )
        )
    )

    assert response.status == "completed"
    assert response.model == "fake-cheap-agent"
    assert response.result is not None
    assert response.result.confidence == 5
    assert response.selfEvaluation is not None
    assert response.selfEvaluation["model"] == "fake-mini"
    assert response.selfEvaluation["verdict"] == "accept"
    assert response.selfEvaluation["humanComparison"]["referenceProvided"] is True
    assert response.usage["totals"]["total_tracked_tokens"] == 165
    assert any(call["model"] == "fake-cheap-agent" for call in client.responses.calls)
    agent_call = next(call for call in client.responses.calls if call.get("tools"))
    assert "Facet Construction Protocol" in agent_call["instructions"]
    assert "Runtime Tool And Output Contract" in agent_call["instructions"]
    learning_path = tmp_path / "learning" / "run_learning.jsonl"
    records = [json.loads(line) for line in learning_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["runStatus"] == "completed"
    assert records[0]["agentModel"] == "fake-cheap-agent"
    assert records[0]["status"] == "analyzed"
    assert records[0]["analysis"]["outcomeType"] == "good_pattern"
    assert records[0]["result"]["constructedCode"] == "A02QF"
    assert any(call["model"] == "fake-mini" for call in client.responses.calls)
    assert any(call["model"] == "fake-smart-model" for call in client.responses.calls)
    eval_call = next(
        call
        for call in client.responses.calls
        if "FoodEx2 coding quality reviewer" in str(call.get("instructions", ""))
    )
    eval_input = json.loads(eval_call["input"])
    assert eval_input["humanReference"] == "A02QF - Fresh uncured cheese"
    assert eval_input["request"]["human_reference"] == "A02QF - Fresh uncured cheese"


def _assert_strict_schema(schema, *, path):
    if not isinstance(schema, dict):
        return

    unsupported_keywords = {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
    }
    assert unsupported_keywords.isdisjoint(schema), path

    if schema.get("type") == "object":
        assert schema.get("additionalProperties") is False, path

    properties = schema.get("properties") or {}
    if properties:
        assert set(schema.get("required", [])) == set(properties), path
        for name, child in properties.items():
            _assert_strict_schema(child, path=f"{path}.{name}")

    items = schema.get("items")
    if items:
        _assert_strict_schema(items, path=f"{path}[]")
