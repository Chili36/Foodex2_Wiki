"""Answer committed source questions through production wiki retrieval and judge gaps."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any, Literal

from evals.coverage.chunk import chunk_sources
from evals.coverage.common import (
    load_yaml,
    local_model_config,
    post_json,
    repo_path,
    resolve_env,
    service_model_name,
    write_json,
)
from evals.coverage.coverage_index import load_manifest, sha256_file
from evals.coverage.local_model import LMStudioModel, require_local_url
from wiki_api.wiki_store import PROMPT_CONTEXT_PAGE_CATEGORIES, WikiStore

VERDICTS = {"covered", "partial", "missing"}
CONSERVATIVE_ORDER = {"missing": 0, "partial": 1, "covered": 2}
EVIDENCE_STOPWORDS = {
    "about", "after", "also", "and", "are", "been", "being", "between", "could",
    "does", "foodex2", "from", "have", "into", "must", "only", "should", "that",
    "their", "these", "this", "through", "when", "where", "which", "with", "would",
}


def _model(config: dict[str, Any], *, allow_remote: bool = False) -> LMStudioModel:
    resolved = resolve_env(config) if allow_remote else local_model_config(config)
    return LMStudioModel(
        model=str(resolved["model"]),
        base_url=str(resolved.get("base_url") or "https://api.openai.com/v1"),
        api_key_env=resolved.get("api_key_env"),
        temperature=float(resolved.get("temperature", 0.0)),
        seed=int(resolved.get("seed", 42)),
        max_tokens=int(resolved.get("max_tokens", 2048)),
        timeout=float(resolved.get("timeout_seconds", 180)),
        max_retries=int(resolved.get("max_retries", 3)),
        allow_remote=allow_remote,
    )


def _contexts(response: dict[str, Any]) -> list[str]:
    contexts = []
    for page in response.get("pages") or []:
        if not isinstance(page, dict):
            continue
        content = page.get("content")
        if isinstance(content, str) and content.strip():
            contexts.append(f"Page: {page.get('page_name', 'unknown')}\n{content.strip()}")
    return contexts


def _evidence_tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", text)
        if len(token) >= 4 and token.casefold() not in EVIDENCE_STOPWORDS
    }


def _markdown_sections(page_name: str, content: str, *, max_chars: int = 4500) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    heading = page_name
    lines: list[str] = []

    def flush() -> None:
        text = "\n".join(lines).strip()
        if not text:
            return
        for start in range(0, len(text), max_chars):
            sections.append(
                {
                    "page_name": page_name,
                    "heading": heading,
                    "content": text[start : start + max_chars],
                }
            )

    for line in content.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if match:
            flush()
            heading = match.group(1).strip()
            lines = []
        else:
            lines.append(line)
    flush()
    return sections


def _rank_sections(
    sections: list[dict[str, str]],
    *,
    query: str,
    limit: int,
    max_total_chars: int,
) -> list[dict[str, str]]:
    query_tokens = _evidence_tokens(query)
    code_tokens = set(re.findall(r"\b(?:A[0-9A-Z]{4}|F\d{2})\b", query, re.I))
    ranked = []
    for section in sections:
        text = f"{section['heading']}\n{section['content']}"
        tokens = _evidence_tokens(text)
        overlap = query_tokens & tokens
        exact_codes = {code.upper() for code in re.findall(r"\b(?:A[0-9A-Z]{4}|F\d{2})\b", text, re.I)}
        score = len(overlap) + 4 * len({code.upper() for code in code_tokens} & exact_codes)
        if score:
            ranked.append((score, len(overlap), section))
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]["page_name"], item[2]["heading"]))
    selected: list[dict[str, str]] = []
    total = 0
    for _, _, section in ranked:
        size = len(section["content"])
        if selected and total + size > max_total_chars:
            continue
        selected.append(section)
        total += size
        if len(selected) >= limit or total >= max_total_chars:
            break
    return selected


def _format_sections(sections: list[dict[str, str]]) -> str:
    return "\n\n---\n\n".join(
        f"Page: {item['page_name']}\nSection: {item['heading']}\n{item['content']}"
        for item in sections
    )


def _wiki_sections(store: WikiStore) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    for page_name in store.list_pages():
        if store.page_categories.get(page_name) not in PROMPT_CONTEXT_PAGE_CATEGORIES:
            continue
        page = store.read_page(page_name)
        sections.extend(_markdown_sections(page_name, page.content))
    return sections


def _retrieved_sections(response: dict[str, Any]) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    for page in response.get("pages") or []:
        if not isinstance(page, dict) or not isinstance(page.get("content"), str):
            continue
        sections.extend(_markdown_sections(str(page.get("page_name") or "unknown"), page["content"]))
    return sections


def _require_local_service_trace(response: dict[str, Any], *, path: str) -> None:
    trace = response.get("trace") or {}
    if path == "context-pack":
        models = [trace.get("model")]
    else:
        models = [
            (trace.get("retrieval") or {}).get("model"),
            (trace.get("answer") or {}).get("model"),
        ]
    non_local = [model for model in models if not str(model or "").casefold().startswith("lmstudio:")]
    if non_local:
        raise RuntimeError(
            "wiki service trace did not prove local-only model routing: "
            f"{non_local}; restart the wiki with its LM Studio base URL configured"
        )


def answer_question(
    *,
    question: str,
    config: dict[str, Any],
    answerer: LMStudioModel,
) -> tuple[str, dict[str, Any]]:
    retrieval = config.get("retrieval") or {}
    wiki_url = require_local_url(str(retrieval.get("wiki_url") or "http://127.0.0.1:8000"))
    path = str(retrieval.get("path") or "context-pack")
    selector = local_model_config(config.get("models", {}).get("selector", {}))
    answerer_config = local_model_config(config.get("models", {}).get("answerer", {}))
    timeout = float(retrieval.get("timeout_seconds", 240))
    max_pages = int(retrieval.get("max_pages", 7))
    if path == "ask":
        response = post_json(
            f"{wiki_url}/wiki/ask",
            {
                "question": question,
                "max_pages": max_pages,
                "include_page_content": True,
                "use_graph_expansion": False,
                "selector_model": service_model_name(selector),
                "answerer_model": service_model_name(answerer_config),
            },
            timeout=timeout,
        )
        _require_local_service_trace(response, path=path)
        return str(response.get("answer") or ""), response
    if path != "context-pack":
        raise ValueError("retrieval.path must be context-pack or ask")
    response = post_json(
        f"{wiki_url}/wiki/context-pack",
        {
            "search_term": question,
            "deconstructed_query": {"question": question},
            "context": {"endpoint": "coverage-eval"},
            "max_pages": max_pages,
            "include_page_content": True,
            "candidate_hints": [],
            "selector_model": service_model_name(selector),
        },
        timeout=timeout,
    )
    _require_local_service_trace(response, path=path)
    contexts = _contexts(response)
    prompt = (
        "Answer the FoodEx2 question using only the retrieved wiki context. "
        "If the context does not support a fact, say so explicitly.\n\n"
        f"Question:\n{question}\n\nRetrieved wiki context:\n"
        + "\n\n---\n\n".join(contexts)
    )
    return str(answerer.generate(prompt)), response


def judge_once(
    *,
    question: str,
    answer: str,
    reference: str,
    qualified_claims: list[dict[str, Any]],
    wiki_evidence: str,
    retrieved_evidence: str,
    judge: LMStudioModel,
) -> dict[str, str]:
    prompt = f"""You are judging three layers of source coverage, not writing the ideal answer.

Return JSON only:
{{"wiki_verdict":"covered|partial|missing","context_verdict":"covered|partial|missing","answer_verdict":"covered|partial|missing","rationale":"one short sentence"}}

Definitions:
- covered: the layer contains all qualified source facts materially needed to answer the question, without contradiction.
- partial: the layer contains some needed facts but omits or weakens at least one material fact.
- missing: the layer lacks the needed facts or contradicts them.

Judge ONLY qualified claims that are materially required by the question. The source chunk
proves provenance but does not make every unrelated sentence a coverage requirement.
`wiki_verdict` evaluates the wiki-wide candidate excerpts. `context_verdict` evaluates only
the production-retrieved excerpts. `answer_verdict` evaluates only the final answer. A
candidate-excerpt miss can be uncertain, so do not call the wiki covered unless its excerpts
actually contain the needed semantic fact.

Question:
{question}

Qualified source claims:
{json.dumps([claim.get('claim') for claim in qualified_claims], ensure_ascii=False)}

Authoritative source chunk:
{reference}

Wiki-wide candidate excerpts:
{wiki_evidence or '[none found]'}

Production-retrieved excerpts:
{retrieved_evidence or '[none retrieved]'}

Wiki-grounded answer:
{answer}
"""
    result = judge.generate_json(
        prompt,
        json_schema={
            "type": "object",
            "properties": {
                "wiki_verdict": {
                    "type": "string",
                    "enum": ["covered", "partial", "missing"],
                },
                "context_verdict": {
                    "type": "string",
                    "enum": ["covered", "partial", "missing"],
                },
                "answer_verdict": {
                    "type": "string",
                    "enum": ["covered", "partial", "missing"],
                },
                "rationale": {"type": "string"},
            },
            "required": ["wiki_verdict", "context_verdict", "answer_verdict", "rationale"],
            "additionalProperties": False,
        },
    )
    rationale = str(result.get("rationale") or "").strip()
    normalized = {
        key: str(result.get(key) or "").casefold().strip()
        for key in ("wiki_verdict", "context_verdict", "answer_verdict")
    }
    if any(verdict not in VERDICTS for verdict in normalized.values()):
        raise ValueError(f"judge returned invalid layered verdicts: {normalized!r}")
    if not rationale or "\n" in rationale:
        raise ValueError("judge rationale must be one non-empty line")
    return {**normalized, "verdict": normalized["answer_verdict"], "rationale": rationale}


def aggregate_judgments(judgments: list[dict[str, str]]) -> dict[str, Any]:
    counts = collections.Counter(item["verdict"] for item in judgments)
    largest = max(counts.values())
    winners = [name for name, count in counts.items() if count == largest]
    verdict = min(winners, key=lambda name: CONSERVATIVE_ORDER[name])
    rationale = next(item["rationale"] for item in judgments if item["verdict"] == verdict)
    return {
        "verdict": verdict,
        "rationale": rationale,
        "repeats": judgments,
        "agreement_percent": round(100 * largest / len(judgments), 2),
        "wiki_verdict": _aggregate_layer(judgments, "wiki_verdict"),
        "context_verdict": _aggregate_layer(judgments, "context_verdict"),
    }


def _aggregate_layer(judgments: list[dict[str, str]], key: str) -> str:
    counts = collections.Counter(item[key] for item in judgments)
    largest = max(counts.values())
    winners = [name for name, count in counts.items() if count == largest]
    return min(winners, key=lambda name: CONSERVATIVE_ORDER[name])


def classify_root_causes(*, wiki_verdict: str, context_verdict: str, answer_verdict: str) -> list[str]:
    if answer_verdict == "covered":
        return []
    causes: list[str] = []
    if wiki_verdict != "covered":
        causes.append("likely_knowledge")
    if CONSERVATIVE_ORDER[wiki_verdict] > CONSERVATIVE_ORDER[context_verdict]:
        causes.append("retrieval")
    if CONSERVATIVE_ORDER[context_verdict] > CONSERVATIVE_ORDER[answer_verdict]:
        causes.append("answerer")
    if not causes:
        causes.append("answerer" if wiki_verdict == "covered" else "likely_knowledge")
    return causes


def effective_wiki_verdict(*, candidate_verdict: str, context_verdict: str) -> str:
    """Retrieved wiki context is direct proof that the represented fact exists in the wiki."""
    return max((candidate_verdict, context_verdict), key=lambda name: CONSERVATIVE_ORDER[name])


def _verify_testset_sources(testset: dict[str, Any], manifest_path: Path) -> None:
    manifest = {source["id"]: source for source in load_manifest(manifest_path)}
    for source in testset.get("sources") or []:
        source_id = source.get("id")
        current = manifest.get(source_id)
        if current is None:
            raise ValueError(f"testset source no longer exists in manifest: {source_id}")
        if source.get("sha256") != current.get("sha256"):
            raise ValueError(f"testset is stale for {source_id}; generate a new versioned testset")
        path = repo_path(current["path"])
        if sha256_file(path) != source.get("sha256"):
            raise ValueError(f"working source hash differs from testset for {source_id}")


def run_coverage(
    *,
    testset_path: Path,
    config_path: Path,
    output_dir: Path,
    judge_repeats: int = 1,
    escalate_judge: bool = False,
    dry_run: bool = False,
    max_cases: int | None = None,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    if judge_repeats < 1:
        raise ValueError("judge_repeats must be at least 1")
    testset = json.loads(testset_path.read_text(encoding="utf-8"))
    config = load_yaml(config_path)
    manifest_path = repo_path(config.get("source_manifest"))
    _verify_testset_sources(testset, manifest_path)
    chunk_max_chars = int(testset.get("generator", {}).get("chunk_max_chars", 6000))
    source_ids = {str(source["id"]) for source in testset.get("sources") or []}
    current_chunks = chunk_sources(manifest_path, max_chars=chunk_max_chars, source_ids=source_ids)
    chunks = {chunk["chunk_id"]: chunk for chunk in current_chunks["chunks"]}
    cases = testset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("testset must contain non-empty cases")
    if case_ids:
        requested = set(case_ids)
        cases = [case for case in cases if str(case.get("id")) in requested]
        found = {str(case.get("id")) for case in cases}
        missing_ids = sorted(requested - found)
        if missing_ids:
            raise ValueError(f"unknown case ids: {missing_ids}")
    if max_cases is not None:
        if max_cases < 1:
            raise ValueError("max_cases must be at least 1")
        cases = cases[:max_cases]
    missing_chunks = sorted({case.get("chunk_id") for case in cases} - set(chunks))
    if missing_chunks:
        raise ValueError(f"testset parent chunks are stale or missing: {missing_chunks[:5]}")
    if dry_run:
        return {
            "dry_run": True,
            "case_count": len(cases),
            "local_answer_calls": len(cases),
            "local_judge_calls": len(cases) * judge_repeats,
            "possible_frontier_escalations": len(cases) if escalate_judge else 0,
            "network_egress_default": False,
        }

    answerer_config = local_model_config(config.get("models", {}).get("answerer", {}))
    judge_config = local_model_config(config.get("models", {}).get("judge", {}))
    answerer = _model(answerer_config)
    judge = _model(judge_config)
    store = WikiStore(repo_path("."))
    all_wiki_sections = _wiki_sections(store)
    escalation_model = None
    if escalate_judge:
        escalation_config = config.get("models", {}).get("escalation_judge")
        if not isinstance(escalation_config, dict):
            raise ValueError("--escalate-judge requires models.escalation_judge config")
        escalation_model = _model(escalation_config, allow_remote=True)

    started = dt.datetime.now(dt.timezone.utc)
    results = []
    for case in cases:
        case_started = time.perf_counter()
        chunk = chunks[case["chunk_id"]]
        try:
            answer, retrieval = answer_question(question=case["question"], config=config, answerer=answerer)
            evidence_query = "\n".join(
                [case["question"], *[str(claim.get("claim") or "") for claim in case.get("qualified_claims") or []]]
            )
            wiki_evidence = _format_sections(
                _rank_sections(
                    all_wiki_sections,
                    query=evidence_query,
                    limit=8,
                    max_total_chars=18000,
                )
            )
            retrieved_evidence = _format_sections(
                _rank_sections(
                    _retrieved_sections(retrieval),
                    query=evidence_query,
                    limit=6,
                    max_total_chars=14000,
                )
            )
            judgments = [
                judge_once(
                    question=case["question"],
                    answer=answer,
                    reference=chunk["text"],
                    qualified_claims=case.get("qualified_claims") or [],
                    wiki_evidence=wiki_evidence,
                    retrieved_evidence=retrieved_evidence,
                    judge=judge,
                )
                for _ in range(judge_repeats)
            ]
            decision = aggregate_judgments(judgments)
            wiki_candidate_verdict = decision["wiki_verdict"]
            decision["wiki_verdict"] = effective_wiki_verdict(
                candidate_verdict=wiki_candidate_verdict,
                context_verdict=decision["context_verdict"],
            )
            escalation = None
            if escalation_model is not None and decision["verdict"] in {"partial", "missing"}:
                escalation = judge_once(
                    question=case["question"],
                    answer=answer,
                    reference=chunk["text"],
                    qualified_claims=case.get("qualified_claims") or [],
                    wiki_evidence=wiki_evidence,
                    retrieved_evidence=retrieved_evidence,
                    judge=escalation_model,
                )
                decision = {**decision, "local_verdict": decision["verdict"], **escalation}
            result = {
                **case,
                "answer": answer,
                "pages_used": retrieval.get("pages_used") or [],
                "verdict": decision["verdict"],
                "wiki_candidate_verdict": wiki_candidate_verdict,
                "wiki_verdict": decision["wiki_verdict"],
                "context_verdict": decision["context_verdict"],
                "root_causes": classify_root_causes(
                    wiki_verdict=decision["wiki_verdict"],
                    context_verdict=decision["context_verdict"],
                    answer_verdict=decision["verdict"],
                ),
                "rationale": decision["rationale"],
                "local_judgments": judgments,
                "agreement_percent": decision["agreement_percent"],
                "escalation": escalation,
                "elapsed_ms": int((time.perf_counter() - case_started) * 1000),
            }
        except Exception as exc:
            result = {
                **case,
                "verdict": "missing",
                "rationale": f"Evaluation error: {type(exc).__name__}: {exc}",
                "error": True,
                "elapsed_ms": int((time.perf_counter() - case_started) * 1000),
            }
        results.append(result)

    counts = collections.Counter(result["verdict"] for result in results)
    per_source = []
    for source_id in sorted(source_ids):
        source_results = [item for item in results if item["source_id"] == source_id]
        source_counts = collections.Counter(item["verdict"] for item in source_results)
        total = len(source_results)
        per_source.append(
            {
                "source_id": source_id,
                "question_count": total,
                "covered": source_counts["covered"],
                "partial": source_counts["partial"],
                "missing": source_counts["missing"],
                "coverage_percent": round(100 * source_counts["covered"] / total, 2) if total else 0.0,
                "covered_or_partial_percent": round(
                    100 * (source_counts["covered"] + source_counts["partial"]) / total, 2
                ) if total else 0.0,
            }
        )
    agreements = [item.get("agreement_percent", 0.0) for item in results if not item.get("error")]
    root_cause_counts = collections.Counter(
        cause for item in results for cause in (item.get("root_causes") or [])
    )
    summary = {
        "testset_id": testset.get("testset_id"),
        "testset": str(testset_path),
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "case_count": len(results),
        "covered": counts["covered"],
        "partial": counts["partial"],
        "missing": counts["missing"],
        "coverage_percent": round(100 * counts["covered"] / len(results), 2),
        "root_cause_counts": dict(sorted(root_cause_counts.items())),
        "per_source": per_source,
        "judge": {
            "model": judge_config["model"],
            "repeats": judge_repeats,
            "mean_agreement_percent": round(statistics.mean(agreements), 2) if agreements else 0.0,
            "cases_with_variance": sum(value < 100 for value in agreements),
        },
        "frontier_escalation_enabled": escalate_judge,
        "network_egress_default": False,
    }
    gaps = [
        {
            key: item.get(key)
            for key in (
                "source_id", "chunk_id", "page_start", "page_end", "section",
                "verdict", "wiki_verdict", "context_verdict", "root_causes",
                "rationale", "question", "id",
            )
        }
        for item in results
        if item["verdict"] in {"partial", "missing"}
    ]
    write_json(output_dir / "results.json", {"summary": summary, "results": results})
    write_json(output_dir / "gaps.json", {"gap_count": len(gaps), "gaps": gaps})
    summary_path = repo_path(
        (config.get("reporting") or {}).get(
            "summary_path", "evals/coverage/reports/summary.json"
        )
    )
    if max_cases is None and not case_ids:
        write_json(summary_path, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--judge-repeats", type=int, default=1)
    parser.add_argument("--escalate-judge", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-cases", type=int, help="Run only the first N frozen cases for a pilot.")
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Run one frozen case by id; repeat to select multiple cases.",
    )
    args = parser.parse_args(argv)
    output_dir = args.output_dir or (
        Path(__file__).parent / "reports" / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    summary = run_coverage(
        testset_path=args.testset.resolve(),
        config_path=args.config.resolve(),
        output_dir=output_dir.resolve(),
        judge_repeats=args.judge_repeats,
        escalate_judge=args.escalate_judge,
        dry_run=args.dry_run,
        max_cases=args.max_cases,
        case_ids=args.case_ids,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
