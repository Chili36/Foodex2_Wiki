"""Independently audit generated coverage questions with a stronger local model."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import yaml

from evals.coverage.common import load_yaml, local_model_config, write_json
from evals.coverage.generate import _non_operational_source_reason, screen_question
from evals.coverage.local_model import LMStudioDeepEvalModel


def _auditor(config: dict[str, Any]) -> tuple[LMStudioDeepEvalModel, dict[str, Any]]:
    configured = (config.get("models") or {}).get("auditor")
    if not isinstance(configured, dict):
        configured = {
            "provider": "lmstudio",
            "model": "env:COVERAGE_AUDITOR_MODEL",
            "base_url": "env:COVERAGE_LMSTUDIO_BASE_URL",
            "temperature": 0,
            "seed": 42,
            "max_tokens": 512,
        }
    resolved = local_model_config(configured)
    return (
        LMStudioDeepEvalModel(
            model=resolved["model"],
            base_url=resolved["base_url"],
            api_key_env=resolved.get("api_key_env"),
            temperature=float(resolved.get("temperature", 0.0)),
            seed=int(resolved.get("seed", 42)),
            max_tokens=int(resolved.get("max_tokens", 512)),
            timeout=float(resolved.get("timeout_seconds", 180)),
            max_retries=int(resolved.get("max_retries", 3)),
        ),
        resolved,
    )


def audit_testset_payload(
    testset: dict[str, Any],
    *,
    auditor: LMStudioDeepEvalModel,
    auditor_config: dict[str, Any],
) -> dict[str, Any]:
    cases = testset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("testset must contain non-empty cases")
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for case in cases:
        claims = [
            claim
            for claim in (case.get("qualified_claims") or [])
            if isinstance(claim, dict)
            and _non_operational_source_reason(
                str(claim.get("claim") or ""),
                str(claim.get("source_evidence") or ""),
            )
            is None
        ]
        generation_screening = case.get("automated_screening")
        if claims:
            screening = screen_question(
                auditor,
                question=str(case.get("question") or ""),
                claims=claims,
            )
            relevant_indexes = screening.get("relevant_claim_indexes") or []
            claims = [claims[index] for index in relevant_indexes]
            if not claims:
                screening = {
                    **screening,
                    "accepted": False,
                    "answerable_from_claims": False,
                    "rationale": "The auditor found no source claim materially required by the question.",
                }
        else:
            screening = {
                "accepted": False,
                "decision_relevant": False,
                "answerable_from_claims": False,
                "quote_dependent": False,
                "decision_axis": "none",
                "rationale": "No operational source claims remain after deterministic filtering.",
            }
        audited_case = {
            **case,
            "qualified_claims": claims,
            "generation_screening": generation_screening,
            "auditor_screening": screening,
        }
        audited_case.pop("automated_screening", None)
        if screening.get("accepted") is True:
            accepted.append(audited_case)
        else:
            rejected.append(
                {
                    "id": case.get("id"),
                    "source_id": case.get("source_id"),
                    "chunk_id": case.get("chunk_id"),
                    "question": case.get("question"),
                    "auditor_screening": screening,
                }
            )
    audited_at = dt.datetime.now(dt.timezone.utc).isoformat()
    original_id = str(testset.get("testset_id") or "coverage-testset")
    result = {
        **testset,
        "testset_id": f"{original_id}-audited",
        "audited_at": audited_at,
        "question_audit": {
            "provider": "lmstudio",
            "model": auditor_config["model"],
            "base_url": auditor_config["base_url"],
            "input_question_count": len(cases),
            "accepted_question_count": len(accepted),
            "rejected_question_count": len(rejected),
            "independent_from_generator": (
                auditor_config["model"] != (testset.get("generator") or {}).get("model")
            ),
        },
        "pre_audit_case_count": len(cases),
        "audit_rejected_questions": rejected,
        "case_count": len(accepted),
        "cases": accepted,
    }
    summary = dict(result.get("qualification_summary") or {})
    summary["pre_audit_question_count"] = len(cases)
    summary["audited_question_count"] = len(accepted)
    summary["auditor_rejected_question_count"] = len(rejected)
    result["qualification_summary"] = summary
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args(argv)
    config = load_yaml(args.config.resolve())
    model, model_config = _auditor(config)
    testset = json.loads(args.testset.read_text(encoding="utf-8"))
    audited = audit_testset_payload(testset, auditor=model, auditor_config=model_config)
    write_json(args.output.resolve(), audited)
    if args.manifest_output:
        manifest = dict(config)
        manifest["testset_id"] = audited["testset_id"]
        manifest["question_audit"] = audited["question_audit"]
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "testset_id": audited["testset_id"],
                **audited["question_audit"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
