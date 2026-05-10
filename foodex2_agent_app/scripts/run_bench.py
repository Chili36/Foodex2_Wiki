"""Bench driver for the FoodEx2 coding agent.

Runs a fixed JSON case file through the real `FoodEx2Agent`, writes a
single bench summary JSON, and (optionally) appends to a token-budget
sidecar that the Ralph Loop watches to self-terminate when the cumulative
spend ceiling is reached.

Usage:
    python scripts/run_bench.py
    python scripts/run_bench.py --bench-id smoketest
    python scripts/run_bench.py --agent-model gpt-5.5 --bench-id final-5.5

Exit code is 0 when all cases pass and at least 4/5 are within their
per-case token budgets; non-zero otherwise. The loop reads the JSON,
not the exit code.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make `foodex2_agent` importable when this script is run directly.
APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from foodex2_agent.agent import _is_hard_warning  # type: ignore  # noqa: E402
from foodex2_agent.app import build_agent  # noqa: E402
from foodex2_agent.models import CodeRequest, CodeResponse  # noqa: E402
from foodex2_agent.prompts import AGENT_MD_PATH  # noqa: E402


DEFAULT_AGENT_MODEL = "gpt-5.4-mini"
DEFAULT_SELF_EVAL_MODEL = "gpt-5.4-mini"
DEFAULT_PER_CASE_BUDGET = 60_000
DEFAULT_BENCH_BUDGET = 350_000
DEFAULT_LOOP_CEILING = 2_500_000

PROJECT_ROOT = APP_ROOT.parent
DEFAULT_BUDGET_SIDECAR = PROJECT_ROOT / ".claude" / "ralph-loop-budget.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", default=str(APP_ROOT / "bench" / "cases.json"),
                        help="Path to the cases JSON file")
    parser.add_argument("--agent-model", default=DEFAULT_AGENT_MODEL,
                        help=f"Override agent model (default: {DEFAULT_AGENT_MODEL})")
    parser.add_argument("--self-evaluation-model", default=DEFAULT_SELF_EVAL_MODEL,
                        help=f"Override self-eval model (default: {DEFAULT_SELF_EVAL_MODEL})")
    parser.add_argument("--max-tool-rounds", type=int, default=None,
                        help="Global cap; per-case max_tool_rounds in cases.json wins if set")
    parser.add_argument("--bench-id", default=None,
                        help="Bench run identifier; default is utc timestamp + '-bench'")
    parser.add_argument("--out", default=None,
                        help="Output JSON path; default logs/bench-<bench-id>.json")
    parser.add_argument("--budget-sidecar", default=str(DEFAULT_BUDGET_SIDECAR),
                        help="Loop-token budget sidecar JSON path")
    parser.add_argument("--no-update-budget", action="store_true",
                        help="Skip appending to the budget sidecar (e.g. for smoke tests)")
    return parser.parse_args(argv)


def classify_error(error: str | None) -> str:
    if not error:
        return "none"
    lower = error.lower()
    if "exceeded max tool rounds" in lower:
        return "agent"
    if any(token in lower for token in ("httpx", "connection refused", "cannot connect", "connecterror", "timeout")):
        return "infra"
    return "agent"


def validator_summary(response: CodeResponse) -> dict[str, Any]:
    result = response.result
    if result is None:
        return {"passes": False, "hardWarnings": 0, "anyWarnings": 0, "raw": None}
    check = result.validationCheck or {}
    warnings = check.get("warnings") or []
    hard_count = sum(1 for w in warnings if _is_hard_warning(w))
    return {
        "passes": bool(check.get("passes")) or bool(check.get("valid")),
        "hardWarnings": hard_count,
        "anyWarnings": len(warnings),
    }


def extract_fact_coverage_risks(response: CodeResponse) -> list[dict[str, Any]]:
    """Return entries from selfEvaluation.sourceFactCoverage with risky statuses.

    Per the plan, only `missed` and `ambiguous` count as risks. Other statuses
    like `unsupported_not_coded` and `covered_by_*` are legitimate dispositions
    and must not fail a case. The agent's own `factCoverage` ledger uses
    different vocabulary (implicit_in_base, not_codeable, etc.) and is NOT the
    bench's gate — the self-evaluator's verdict is.
    """
    se = response.selfEvaluation or {}
    coverage = se.get("sourceFactCoverage") or []
    risky_statuses = {"missed", "ambiguous"}
    return [
        entry for entry in coverage
        if isinstance(entry, dict)
        and str(entry.get("status") or "").lower() in risky_statuses
    ]


def extract_self_evaluation(response: CodeResponse) -> dict[str, Any]:
    se = response.selfEvaluation or {}
    return {
        "model": se.get("model"),
        "verdict": se.get("verdict"),
        "score": se.get("score"),
        "codingRisks": se.get("codingRisks") or [],
        "sourceFactCoverage": se.get("sourceFactCoverage") or [],
        "humanComparison": se.get("humanComparison"),
        "recommendedNextAction": se.get("recommendedNextAction"),
    }


def evaluate_pass(case_result: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if case_result["status"] != "completed":
        reasons.append("status_not_completed")
        return False, reasons

    validator = case_result["validator"]
    if not validator["passes"]:
        reasons.append("validator_failed")
    if validator["hardWarnings"] > 0:
        reasons.append("validator_hard_warning")

    se = case_result["selfEvaluation"]
    verdict = (se.get("verdict") or "").lower()
    score = se.get("score")
    if verdict == "revise":
        reasons.append("verdict_revise")
    elif verdict not in {"accept", "review"}:
        reasons.append("verdict_unknown")
    elif verdict == "review" and (not isinstance(score, (int, float)) or score < 4):
        reasons.append("review_low_score")

    if case_result["factCoverageRisks"]:
        reasons.append("fact_coverage_risk")

    return (not reasons), reasons


def token_spend_summary(response: CodeResponse, budget: int) -> dict[str, Any]:
    usage = response.usage or {}
    totals = usage.get("totals") or {}
    by_model = usage.get("by_model") or []
    total = int(totals.get("total_tracked_tokens") or 0)
    return {
        "total": total,
        "input": int(totals.get("input_tokens") or 0),
        "output": int(totals.get("output_tokens") or 0),
        "byModel": [
            {"model": item.get("model"), "total": int(item.get("total_tracked_tokens") or 0),
             "calls": int(item.get("calls") or 0)}
            for item in by_model
        ],
        "budget": budget,
        "withinBudget": total <= budget,
    }


async def run_case(agent, case: dict[str, Any], *, agent_model: str, self_eval_model: str,
                   global_max_rounds: int | None) -> dict[str, Any]:
    case_id = str(case.get("id"))
    search_term = str(case.get("search_term"))
    token_budget = int(case.get("token_budget") or DEFAULT_PER_CASE_BUDGET)
    max_rounds = case.get("max_tool_rounds")
    if max_rounds is None:
        max_rounds = global_max_rounds

    request = CodeRequest(
        search_term=search_term,
        language_hint=case.get("language_hint"),
        domain=case.get("domain"),
        human_reference=case.get("human_reference"),
        agent_model=agent_model,
        self_evaluation_model=self_eval_model,
        max_tool_rounds=max_rounds,
        audit_mode=True,
    )

    response: CodeResponse = await agent.run(request)

    error = response.error
    error_class = classify_error(error)
    max_rounds_hit = bool(error and error.lower().startswith("exceeded max tool rounds"))
    validator = validator_summary(response)
    self_eval = extract_self_evaluation(response)
    fact_risks = extract_fact_coverage_risks(response)
    token_spend = token_spend_summary(response, token_budget)
    constructed = response.result.constructedCode if response.result is not None else None

    case_result: dict[str, Any] = {
        "case_id": case_id,
        "search_term": search_term,
        "expected_code": case.get("expected_code"),
        "runId": response.runId,
        "logFile": response.logFile,
        "status": response.status,
        "error": error,
        "errorClass": error_class,
        "toolCallCount": len(response.trace),
        "maxToolRoundsHit": max_rounds_hit,
        "validator": validator,
        "selfEvaluation": self_eval,
        "factCoverageRisks": fact_risks,
        "tokenSpend": token_spend,
        "constructedCode": constructed,
        "humanComparison": self_eval.get("humanComparison"),
        "runLearningLog": str((APP_ROOT / "logs" / "run_learning.jsonl")),
        "failureLearningLog": str((APP_ROOT / "logs" / "failure_learning.jsonl")),
    }
    passed, reasons = evaluate_pass(case_result)
    case_result["passed"] = passed
    case_result["failReasons"] = reasons
    return case_result


def load_cases(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"cases": data,
                "bench_token_budget": DEFAULT_BENCH_BUDGET,
                "loop_token_ceiling": DEFAULT_LOOP_CEILING}
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"Bad cases file {path}: must be a list or an object with a 'cases' key")
    data.setdefault("bench_token_budget", DEFAULT_BENCH_BUDGET)
    data.setdefault("loop_token_ceiling", DEFAULT_LOOP_CEILING)
    return data


def agent_md_sha() -> str:
    return hashlib.sha256(AGENT_MD_PATH.read_bytes()).hexdigest()[:12]


def previous_bench_total(out_dir: Path, current_id: str) -> int | None:
    """Return the most recent prior bench's tokenSpend.total, or None."""
    candidates = sorted(
        (p for p in out_dir.glob("bench-*.json") if current_id not in p.name),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            total = data.get("summary", {}).get("tokenSpend", {}).get("total")
            if isinstance(total, int):
                return total
        except (OSError, ValueError):
            continue
    return None


def update_budget_sidecar(path: Path, bench_id: str, agent_md: str,
                          summary: dict[str, Any]) -> dict[str, Any]:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {"cumulativeTokens": 0,
                             "loop_token_ceiling": DEFAULT_LOOP_CEILING,
                             "iterations": []}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    spent = int(summary["tokenSpend"]["total"])
    state["cumulativeTokens"] = int(state.get("cumulativeTokens", 0)) + spent
    iterations = list(state.get("iterations") or [])
    iterations.append({
        "benchRunId": bench_id,
        "agentMdSha": agent_md,
        "tokenSpend": spent,
        "passed": summary["passed"],
        "total": summary["total"],
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    state["iterations"] = iterations
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


async def main_async(argv: list[str]) -> int:
    args = parse_args(argv)
    cases_path = Path(args.cases)
    cases_doc = load_cases(cases_path)

    bench_id = args.bench_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-bench")
    out_path = Path(args.out) if args.out else (APP_ROOT / "logs" / f"bench-{bench_id}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    agent = build_agent()
    case_results: list[dict[str, Any]] = []
    for case in cases_doc["cases"]:
        print(f"[bench] running case: {case.get('id')} ({case.get('search_term')!r})", flush=True)
        result = await run_case(
            agent, case,
            agent_model=args.agent_model,
            self_eval_model=args.self_evaluation_model,
            global_max_rounds=args.max_tool_rounds,
        )
        case_results.append(result)
        print(f"[bench]   passed={result['passed']} reasons={result['failReasons']} "
              f"tokens={result['tokenSpend']['total']}", flush=True)

    totals_tokens = sum(int(r["tokenSpend"]["total"]) for r in case_results)
    per_case_tokens = sorted(int(r["tokenSpend"]["total"]) for r in case_results)
    median = per_case_tokens[len(per_case_tokens) // 2] if per_case_tokens else 0
    over_budget_ids = [r["case_id"] for r in case_results if not r["tokenSpend"]["withinBudget"]]
    max_rounds_hit = sum(1 for r in case_results if r["maxToolRoundsHit"])
    infra_skipped = sum(1 for r in case_results if r["errorClass"] == "infra")
    failing_ids = [r["case_id"] for r in case_results if not r["passed"]]
    passed_count = sum(1 for r in case_results if r["passed"])

    previous_total = previous_bench_total(out_path.parent, bench_id)
    if previous_total and previous_total > 0:
        delta_pct = ((totals_tokens - previous_total) / previous_total) * 100
        delta_str = f"{delta_pct:+.1f}%"
    else:
        delta_str = "n/a"

    summary = {
        "total": len(case_results),
        "passed": passed_count,
        "failed": len(case_results) - passed_count,
        "maxToolRoundsHit": max_rounds_hit,
        "infraSkipped": infra_skipped,
        "failingCaseIds": failing_ids,
        "tokenSpend": {
            "total": totals_tokens,
            "medianPerCase": median,
            "overBudgetCaseIds": over_budget_ids,
            "vsPreviousIterationDelta": delta_str,
        },
    }

    bench_doc = {
        "benchRunId": bench_id,
        "agentMdPath": str(AGENT_MD_PATH),
        "agentMdSha": agent_md_sha(),
        "agentModel": args.agent_model,
        "selfEvaluationModel": args.self_evaluation_model,
        "casesFile": str(cases_path),
        "cases": case_results,
        "summary": summary,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    out_path.write_text(json.dumps(bench_doc, indent=2) + "\n", encoding="utf-8")
    print(f"[bench] wrote {out_path}", flush=True)

    if not args.no_update_budget:
        sidecar_state = update_budget_sidecar(Path(args.budget_sidecar), bench_id,
                                              bench_doc["agentMdSha"], summary)
        loop_ceiling = int(cases_doc.get("loop_token_ceiling") or DEFAULT_LOOP_CEILING)
        cumulative = int(sidecar_state.get("cumulativeTokens") or 0)
        print(f"[bench] budget sidecar: cumulative={cumulative} ceiling={loop_ceiling}",
              flush=True)

    all_pass = passed_count == len(case_results) and len(over_budget_ids) <= 1
    return 0 if all_pass else 1


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    return asyncio.run(main_async(argv))


if __name__ == "__main__":
    raise SystemExit(main())
