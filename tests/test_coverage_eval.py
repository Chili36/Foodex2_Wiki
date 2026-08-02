from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from evals.coverage.chunk import chunk_sources
from evals.coverage.audit import audit_testset_payload
from evals.coverage.coverage_index import build_index
from evals.coverage.generate import (
    _complete_truncated_evidence,
    _non_operational_source_reason,
    _priority_rule_candidates,
    _unsupported_claim_terms,
    qualify_chunk,
    screen_question,
)
from evals.coverage.local_model import _transient_http_error, require_local_url
from evals.coverage.run import (
    aggregate_judgments,
    classify_root_causes,
    effective_wiki_verdict,
    run_coverage,
)
from evals.coverage.staleness import compare_manifests

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "coverage"


class _FakeQualificationModel:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def generate_json(self, prompt: str, **kwargs: object) -> dict:
        if "Verify whether each FoodEx2 claim" in prompt:
            return {
                "verifications": [
                    {
                        "index": 0,
                        "unsupported_additions": [],
                        "entailed": True,
                        "rationale": "Evidence states the claim.",
                    }
                ]
            }
        return self.payload


class _SequentialScreenModel:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)

    def generate_json(self, prompt: str, **kwargs: object) -> dict:
        return self.payloads.pop(0)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lm_link_keepalive_failure_is_retryable() -> None:
    assert _transient_http_error(400, "peer_keepalive_timeout") is True
    assert _transient_http_error(400, "invalid response_format") is False


def test_rule_candidates_surface_decision_language_without_examples() -> None:
    candidates = _priority_rule_candidates(
        "The report was published in 2015. Herbal materials remain raw primary commodities. "
        "A dismissed term must not be used."
    )
    assert candidates == [
        "Herbal materials remain raw primary commodities.",
        "A dismissed term must not be used.",
    ]


def test_truncated_evidence_expands_only_to_unique_complete_sentence() -> None:
    source = "The dismissed FoodEx2 term must not be used. Another statement follows."
    assert (
        _complete_truncated_evidence("The dismissed FoodEx2 term must...", source)
        == "The dismissed FoodEx2 term must not be used."
    )


def test_claim_term_gate_catches_scope_inflation() -> None:
    unsupported = _unsupported_claim_terms(
        "Dismissed or candidate terms are optional for future deprecation.",
        "Dismissed terms have their applicability changed to optional.",
    )
    assert "candidate" in unsupported
    assert "future" in unsupported
    assert "deprecation" in unsupported


def test_source_gate_rejects_toc_lines_and_catalogue_statistics() -> None:
    assert _non_operational_source_reason(
        "Derivatives of raw commodities as a base term",
        "5.1.6. Derivatives of raw commodities ........................................ 41",
    ) == "table_of_contents_or_heading"
    assert _non_operational_source_reason(
        "1112 new terms were added to the catalogue.",
        "In total, 1112 new terms have been added to the catalogue since release 15.0.",
    ) == "administrative_or_catalogue_statistic"
    assert _non_operational_source_reason(
        "Grinding may be applied directly to a raw commodity.",
        "Grinding may be applied directly to a raw commodity when it creates no new nature.",
    ) is None


def _write_manifest(path: Path, source_path: Path, *, version: str = "1") -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "sources": [
                    {
                        "id": "fixture-source",
                        "title": "Authoritative fixture",
                        "version": version,
                        "sha256": _sha(source_path),
                        "path": str(source_path.relative_to(ROOT)),
                        "aliases": ["fixture guidance"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_coverage_index_is_no_model_and_lists_uncovered_sections() -> None:
    report = build_index()
    assert report["model_calls"] == 0
    assert report["section_count"] > report["covered_section_count"]
    assert any(source["uncovered_sections"] for source in report["sources"])


def test_chunk_ids_are_stable_and_trace_to_source_location(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest, FIXTURES / "source-current.md")
    first = chunk_sources(manifest, max_chars=6000)
    second = chunk_sources(manifest, max_chars=6000)
    assert first == second
    chunk = first["chunks"][0]
    assert chunk["source_id"] == "fixture-source"
    assert chunk["section"] == "Authoritative fixture"
    assert chunk["chunk_id"].startswith("fixture-source:s0001:")


def test_local_model_guard_rejects_public_endpoints() -> None:
    assert require_local_url("http://127.0.0.1:1234/v1").endswith("/v1")
    assert require_local_url("http://192.168.1.22:1234/v1").endswith("/v1")
    with pytest.raises(ValueError, match="rejects non-local"):
        require_local_url("https://api.openai.com/v1")


def test_judge_ties_resolve_conservatively_and_report_variance() -> None:
    result = aggregate_judgments(
        [
            {"verdict": "covered", "wiki_verdict": "covered", "context_verdict": "covered", "rationale": "complete"},
            {"verdict": "missing", "wiki_verdict": "partial", "context_verdict": "missing", "rationale": "unsupported"},
        ]
    )
    assert result["verdict"] == "missing"
    assert result["agreement_percent"] == 50.0
    assert result["wiki_verdict"] == "partial"
    assert result["context_verdict"] == "missing"


def test_root_cause_classification_separates_layers() -> None:
    assert classify_root_causes(
        wiki_verdict="covered", context_verdict="missing", answer_verdict="missing"
    ) == ["retrieval"]
    assert classify_root_causes(
        wiki_verdict="covered", context_verdict="covered", answer_verdict="missing"
    ) == ["answerer"]
    assert classify_root_causes(
        wiki_verdict="missing", context_verdict="missing", answer_verdict="missing"
    ) == ["likely_knowledge"]
    assert effective_wiki_verdict(candidate_verdict="partial", context_verdict="covered") == "covered"


def test_qualification_keeps_key_facts_and_excludes_incidental_details() -> None:
    model = _FakeQualificationModel(
        {
            "claims": [
                {
                    "claim": "Herbal infusion materials remain raw.",
                    "category": "exception",
                    "decision_axis": "base_term",
                    "coverage_expectation": "required",
                    "source_evidence": "Herbal infusion materials remain raw",
                    "rationale": "This changes base-term selection.",
                },
                {
                    "claim": "The heading uses the word fixture.",
                    "category": "incidental",
                    "decision_axis": "none",
                    "coverage_expectation": "exclude",
                    "source_evidence": "Authoritative fixture",
                    "rationale": "Publication wording is not operational.",
                },
            ]
        }
    )
    result = qualify_chunk(
        model,  # type: ignore[arg-type]
        {
            "chunk_id": "fixture:p0001:01",
            "text": "Authoritative fixture. Herbal infusion materials remain raw.",
        },
        {},
    )
    assert [claim["category"] for claim in result["eligible_claims"]] == ["exception"]
    assert result["excluded_claims"][0]["exclusion_reason"] == (
        "non_operational_category,no_concrete_decision_axis,not_required,unverified_source_evidence"
    )
    assert result["extraction_claim_count"] == 2
    assert result["audit_claim_count"] == 0


def test_question_screen_rejects_quote_or_page_recall() -> None:
    claims = [{"claim": "Marketed-dry herbal infusion material remains raw."}]
    accepted = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "base_term",
                "rationale": "Tests an ontology exception.",
            }
        ),  # type: ignore[arg-type]
        question="Does normal drying make herbal infusion material a derivative?",
        claims=claims,  # type: ignore[arg-type]
    )
    rejected = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "base_term",
                "rationale": "Incorrect model classification should be caught mechanically.",
            }
        ),  # type: ignore[arg-type]
        question="What does page 42 say about herbal infusions?",
        claims=claims,  # type: ignore[arg-type]
    )
    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert rejected["quote_dependent"] is True


def test_question_screen_rejects_administrative_maintenance_history() -> None:
    result = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "ontology_boundary",
                "rationale": "Model incorrectly treated history as operational.",
            }
        ),  # type: ignore[arg-type]
        question="What was the purpose of FoodEx2 maintenance in 2015?",
        claims=[{"claim": "Maintenance evaluated stakeholder feedback."}],  # type: ignore[list-item]
    )
    assert result["accepted"] is False
    assert result["administrative_only"] is True


def test_question_screen_rejects_self_contradicting_acceptance() -> None:
    result = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "code_construction",
                "rationale": "The qualified claims do not contain enough information to answer definitively.",
            }
        ),  # type: ignore[arg-type]
        question="How should the missing derivative be constructed?",
        claims=[{"claim": "A detailed derivative is missing."}],  # type: ignore[list-item]
    )
    assert result["accepted"] is False
    assert result["self_contradicting_rationale"] is True


def test_question_screen_rejects_exact_code_request_without_code_evidence() -> None:
    result = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "code_construction",
                "rationale": "Tests code construction.",
            }
        ),  # type: ignore[arg-type]
        question="What is the FoodEx2 code for processed commodities?",
        claims=[{"claim": "Processed commodities are derivatives."}],  # type: ignore[list-item]
    )
    assert result["accepted"] is False
    assert result["unsupported_exact_code_request"] is True


def test_question_screen_rejects_historical_term_recall_and_broad_synthesis() -> None:
    model_payload = {
        "decision_relevant": True,
        "answerable_from_claims": True,
        "quote_dependent": False,
        "decision_axis": "facet",
        "rationale": "The model incorrectly treated source recall as a coding decision.",
    }
    recall = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="What new term was added to F28 based on a request from FAO?",
        claims=[{"claim": "A18TD Air-frying was added to F28."}],  # type: ignore[list-item]
    )
    broad = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="How do these definitions collectively refine the system's ability to represent foods?",
        claims=[{"claim": "Raw, derivative and composite foods have distinct definitions."}],  # type: ignore[list-item]
    )
    assert recall["accepted"] is False
    assert recall["historical_recall"] is True
    assert broad["accepted"] is False
    assert broad["broad_explanatory"] is True


def test_question_screen_rejects_catalogue_lookup_and_source_framing() -> None:
    model_payload = {
        "decision_relevant": True,
        "answerable_from_claims": True,
        "quote_dependent": False,
        "decision_axis": "base_term",
        "rationale": "The model treated source recall as an operational decision.",
    }
    lookup = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="What is the FoodEx2 code for Rhinoceros (live animals)?",
        claims=[{"claim": "Rhinoceros has catalogue code A1234."}],  # type: ignore[list-item]
    )
    framed = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="What is the priority order in FoodEx2 revision 2 Table 6?",
        claims=[{"claim": "A narrower processed group takes priority."}],  # type: ignore[list-item]
    )
    assert lookup["accepted"] is False
    assert lookup["catalogue_recall"] is True
    assert framed["accepted"] is False
    assert framed["source_framed"] is True


def test_question_screen_rejects_guidance_history_and_invented_procedure() -> None:
    model_payload = {
        "decision_relevant": True,
        "answerable_from_claims": True,
        "quote_dependent": False,
        "decision_axis": "reporting",
        "rationale": "The model incorrectly accepted an inflated question.",
    }
    history = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="What rule did EFSA establish in its 2015 guidance?",
        claims=[{"claim": "Hierarchy terms must not be reported."}],  # type: ignore[list-item]
    )
    procedure = screen_question(
        _FakeQualificationModel(model_payload),  # type: ignore[arg-type]
        question="What steps should I follow to determine reportability?",
        claims=[{"claim": "Terms with a specific animal source are reportable."}],  # type: ignore[list-item]
    )
    assert history["accepted"] is False
    assert history["source_framed"] is True
    assert procedure["accepted"] is False
    assert procedure["procedure_inflation"] is True


def test_independent_audit_freezes_only_accepted_questions() -> None:
    testset = {
        "testset_id": "fixture-v1",
        "generator": {"model": "qwen"},
        "qualification_summary": {},
        "cases": [
            {
                "id": "good",
                "question": "When should F27 be used?",
                "qualified_claims": [
                    {
                        "claim": "F27 describes the commodity from which a derivative originates.",
                        "source_evidence": "F27 describes the commodity from which a derivative originates.",
                    }
                ],
                "automated_screening": {"accepted": True},
            },
            {
                "id": "bad",
                "question": "What is the purpose of the maintenance report?",
                "qualified_claims": [
                    {
                        "claim": "The report describes maintenance.",
                        "source_evidence": "The report describes maintenance.",
                    }
                ],
                "automated_screening": {"accepted": True},
            },
        ],
    }
    model = _SequentialScreenModel(
        [
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "facet",
                "rationale": "Distinguishes using F27 from omitting it.",
            },
            {
                "decision_relevant": False,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "none",
                "rationale": "Document purpose is not a coding choice.",
            },
        ]
    )
    audited = audit_testset_payload(
        testset,
        auditor=model,  # type: ignore[arg-type]
        auditor_config={"model": "gemma", "base_url": "http://127.0.0.1:1234/v1"},
    )
    assert audited["testset_id"] == "fixture-v1-audited"
    assert [case["id"] for case in audited["cases"]] == ["good"]
    assert audited["question_audit"]["accepted_question_count"] == 1
    assert audited["question_audit"]["independent_from_generator"] is True
    assert audited["audit_rejected_questions"][0]["id"] == "bad"


def test_independent_audit_keeps_only_question_relevant_claims() -> None:
    testset = {
        "testset_id": "fixture-v1",
        "generator": {"model": "qwen"},
        "cases": [
            {
                "id": "focused",
                "question": "What is the difference between dismissed and deprecated terms?",
                "qualified_claims": [
                    {
                        "claim": "Some terms gain facet applicability.",
                        "source_evidence": "Some terms gain facet applicability.",
                    },
                    {
                        "claim": "Dismissed terms remain reportable elsewhere; deprecated terms do not.",
                        "source_evidence": "Dismissed terms remain reportable elsewhere; deprecated terms do not.",
                    },
                ],
            }
        ],
    }
    model = _SequentialScreenModel(
        [
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "validation",
                "relevant_claim_indexes": [1],
                "rationale": "Distinguishes hierarchy-specific from global non-reportability.",
            }
        ]
    )
    audited = audit_testset_payload(
        testset,
        auditor=model,  # type: ignore[arg-type]
        auditor_config={"model": "gemma", "base_url": "http://127.0.0.1:1234/v1"},
    )
    assert [claim["claim"] for claim in audited["cases"][0]["qualified_claims"]] == [
        "Dismissed terms remain reportable elsewhere; deprecated terms do not."
    ]


def test_question_screen_infers_one_unambiguous_claim_axis() -> None:
    result = screen_question(
        _FakeQualificationModel(
            {
                "decision_relevant": True,
                "answerable_from_claims": True,
                "quote_dependent": False,
                "decision_axis": "none",
                "rationale": "The choice affects base-term selection.",
            }
        ),  # type: ignore[arg-type]
        question="Should dried Camellia leaves use a raw or derivative base term?",
        claims=[{"claim": "Camellia follows the derivative approach.", "decision_axis": "base_term"}],  # type: ignore[list-item]
    )
    assert result["accepted"] is True
    assert result["decision_axis"] == "base_term"
    assert result["decision_axis_inferred_from_claims"] is True


class _CoverageHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path == "/wiki/context-pack":
            assert payload["selector_model"].startswith("lmstudio:")
            response = {
                "pages_used": ["base-term-selection.md"],
                "pages": [
                    {
                        "page_name": "base-term-selection.md",
                        "content": "Herbal infusion materials remain raw when normally marketed dry.",
                    }
                ],
                "trace": {"model": payload["selector_model"]},
            }
        elif self.path == "/v1/chat/completions":
            prompt = "\n".join(item.get("content", "") for item in payload["messages"])
            if "source coverage" in prompt:
                content = json.dumps(
                    {
                        "wiki_verdict": "covered",
                        "context_verdict": "covered",
                        "answer_verdict": "covered",
                        "rationale": "The answer states the material marketed-dry rule.",
                    }
                )
            else:
                content = "Herbal infusion materials remain raw when drying is their normally marketed state."
            response = {"choices": [{"message": {"content": content}}]}
        else:
            self.send_error(404)
            return
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def test_full_coverage_run_uses_local_retrieval_answerer_and_judge(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CoverageHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        manifest = tmp_path / "manifest.yaml"
        _write_manifest(manifest, FIXTURES / "source-current.md")
        chunk = chunk_sources(manifest, max_chars=6000)["chunks"][0]
        testset = tmp_path / "testset.json"
        testset.write_text(
            json.dumps(
                {
                    "version": 1,
                    "testset_id": "fixture-v1",
                    "sources": [
                        {"id": "fixture-source", "version": "1", "sha256": _sha(FIXTURES / "source-current.md")}
                    ],
                    "generator": {"chunk_max_chars": 6000},
                    "cases": [
                        {
                            "id": "COV-FIXTURE",
                            "question": "How is normally dried herbal infusion material classified?",
                            "source_id": "fixture-source",
                            "chunk_id": chunk["chunk_id"],
                            "section": chunk["section"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        port = server.server_address[1]
        config = tmp_path / "config.yaml"
        model = {
            "provider": "lmstudio",
            "model": "fixture-model",
            "base_url": f"http://127.0.0.1:{port}/v1",
        }
        config.write_text(
            yaml.safe_dump(
                {
                    "source_manifest": str(manifest),
                    "retrieval": {
                        "path": "context-pack",
                        "wiki_url": f"http://127.0.0.1:{port}",
                        "max_pages": 7,
                    },
                    "models": {
                        "selector": model,
                        "answerer": model,
                        "judge": model,
                    },
                    "reporting": {"summary_path": str(tmp_path / "summary.json")},
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        summary = run_coverage(
            testset_path=testset,
            config_path=config,
            output_dir=tmp_path / "run",
            judge_repeats=2,
        )
        assert summary["coverage_percent"] == 100.0
        assert summary["network_egress_default"] is False
        assert summary["judge"]["mean_agreement_percent"] == 100.0
        result = json.loads((tmp_path / "run" / "results.json").read_text())
        assert result["results"][0]["pages_used"] == ["base-term-selection.md"]
        selected = run_coverage(
            testset_path=testset,
            config_path=config,
            output_dir=tmp_path / "selected",
            dry_run=True,
            case_ids=["COV-FIXTURE"],
        )
        assert selected["case_count"] == 1
    finally:
        server.shutdown()
        thread.join()


def test_staleness_flags_changed_source_revision(tmp_path: Path) -> None:
    old_manifest = tmp_path / "old.yaml"
    new_manifest = tmp_path / "new.yaml"
    _write_manifest(old_manifest, FIXTURES / "source-old.md", version="old")
    _write_manifest(new_manifest, FIXTURES / "source-new.md", version="new")
    report = compare_manifests(old_manifest, new_manifest)
    assert report["model_calls"] == 0
    assert report["changed_sources"][0]["source_id"] == "fixture-source"
    assert report["changed_sources"][0]["changed_pages"] == [1]
