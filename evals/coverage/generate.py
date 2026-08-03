"""Generate commit-ready source-driven questions with a local model."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

import yaml

from evals.coverage.chunk import chunk_sources
from evals.coverage.common import load_yaml, local_model_config, repo_path, write_json
from evals.coverage.coverage_index import DEFAULT_MANIFEST, REPO_ROOT, load_manifest
from evals.coverage.local_model import LMStudioModel

QUESTION_STYLE_ALIASES = {
    "reasoning": "reasoning",
    "multi-hop": "multi-hop",
    "multicontext": "multi-hop",
    "concretising": "concretising",
    "concretizing": "concretising",
    "comparative": "comparative",
}
QUESTION_STYLE_GUIDANCE = {
    "reasoning": "Require applying the supplied rule to choose a coding or reporting action.",
    "multi-hop": "Combine two supplied claims that genuinely need to be applied together.",
    "concretising": "Turn the rule into a concrete decision without inventing a catalogue term or code.",
    "comparative": "Contrast two plausible coding actions and ask which one follows the supplied rule.",
}
DEFAULT_ELIGIBLE_CATEGORIES = {"operational", "structural", "exception"}
GENERATION_PIPELINE_VERSION = 21
CLAIM_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can",
    "could", "for", "from", "in", "into", "is", "it", "its", "like", "may",
    "must", "no", "not", "of", "on", "only", "or", "rather", "should", "than",
    "that", "the", "their", "them", "they", "this", "to", "under", "was", "were",
    "while", "will", "with", "would",
}
DECISION_AXES = {
    "base_term",
    "facet",
    "code_construction",
    "validation",
    "reporting",
    "ontology_boundary",
}

TOC_OR_HEADING_PATTERN = re.compile(
    r"(?:\.{5,}\s*\d*\s*$|^\s*\d+(?:\.\d+){1,5}\.?\s+[^.!?]{1,160}$)",
    re.I,
)
ADMINISTRATIVE_CLAIM_PATTERN = re.compile(
    r"\b(?:pilot project|stakeholder feedback|internal users?|project team|"
    r"maintenance window|publication|published|reporting period)\b|"
    r"\b\d[\d,]*\s+(?:new\s+)?(?:terms?|scope notes?|entries|descriptors?)\b|"
    r"\b(?:terms?|scope notes?)\s+(?:were|have been)\s+(?:added|updated|removed)\b",
    re.I,
)


def _non_operational_source_reason(claim: str, evidence: str) -> str | None:
    """Return a deterministic reason for source text that cannot test wiki decisions."""
    combined = f"{claim}\n{evidence}".strip()
    if TOC_OR_HEADING_PATTERN.search(evidence.strip()):
        return "table_of_contents_or_heading"
    if ADMINISTRATIVE_CLAIM_PATTERN.search(combined):
        return "administrative_or_catalogue_statistic"
    return None


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _source_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9‘'\"])", normalized)


def _priority_rule_candidates(text: str, *, limit: int = 12) -> list[str]:
    sentences = _source_sentences(text)
    cue = re.compile(
        r"\b(?:must|should|shall|required|not allowed|cannot|discouraged|preferred|"
        r"decided|still valid|raw primary commodit(?:y|ies)|derivative|implicit facet|"
        r"applicability|dismissed|optional|base term|facet descriptor|does not create|"
        r"changing the nature)\b",
        re.I,
    )
    return [sentence for sentence in sentences if cue.search(sentence)][:limit]


def _complete_truncated_evidence(evidence: str, source_text: str) -> str:
    marker = re.search(r"(?:\.\.\.|…)", evidence)
    if not marker:
        return evidence
    prefix = _normalized_text(evidence[: marker.start()])
    if len(prefix) < 24:
        return evidence
    matches = [
        sentence
        for sentence in _source_sentences(source_text)
        if prefix in _normalized_text(sentence)
    ]
    return matches[0] if len(matches) == 1 else evidence


def _claim_token(value: str) -> str:
    token = value.casefold()
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    for suffix in ("ing", "ed"):
        if len(token) > len(suffix) + 4 and token.endswith(suffix):
            return token[: -len(suffix)]
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def _unsupported_claim_terms(claim: str, evidence: str) -> list[str]:
    evidence_tokens = {
        _claim_token(token)
        for token in re.findall(r"[A-Za-z0-9]+", evidence)
        if token.casefold() not in CLAIM_STOPWORDS
    }
    unsupported = []
    for token in re.findall(r"[A-Za-z0-9]+", claim):
        lowered = token.casefold()
        if lowered in CLAIM_STOPWORDS or (len(lowered) < 4 and not any(ch.isdigit() for ch in lowered)):
            continue
        if _claim_token(lowered) not in evidence_tokens and lowered not in unsupported:
            unsupported.append(lowered)
    return unsupported


def verify_claim_entailment(
    model: LMStudioModel, claims: list[dict[str, str]]
) -> list[dict[str, Any]]:
    if not claims:
        return []
    prompt = f"""Verify whether each FoodEx2 claim is fully entailed by its evidence sentence.

Return JSON only:
{{"verifications":[{{"index":0,"unsupported_additions":["exact claim phrase not supported by evidence"],"entailed":false,"rationale":"one short sentence"}}]}}

Use only the paired evidence. First extract every phrase in the CLAIM whose meaning is not
stated by the EVIDENCE into `unsupported_additions`. Check subjects, set membership,
conditions, scope, status, time, codes, actions, reasons, and consequences. For example,
evidence about "X items" does not support a claim about "X or Y items"; evidence that a
status changed does not support an unstated reason or consequence. `entailed` may be true
only when `unsupported_additions` is empty. A concise paraphrase is allowed. Return exactly
one result for every index.

Pairs:
{json.dumps([{"index": index, "claim": claim["claim"], "evidence": claim["source_evidence"]} for index, claim in enumerate(claims)], ensure_ascii=False)}
"""
    payload = model.generate_json(
        prompt,
        json_schema={
            "type": "object",
            "properties": {
                "verifications": {
                    "type": "array",
                    "minItems": len(claims),
                    "maxItems": len(claims),
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "minimum": 0},
                            "unsupported_additions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "entailed": {"type": "boolean"},
                            "rationale": {"type": "string"},
                        },
                        "required": ["index", "unsupported_additions", "entailed", "rationale"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["verifications"],
            "additionalProperties": False,
        },
    )
    verifications = payload.get("verifications")
    if not isinstance(verifications, list):
        raise ValueError("claim entailment verifier returned no verifications list")
    by_index = {
        item.get("index"): item
        for item in verifications
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    if set(by_index) != set(range(len(claims))):
        raise ValueError("claim entailment verifier did not return every claim index exactly once")
    return [by_index[index] for index in range(len(claims))]


def qualify_chunk(
    model: LMStudioModel,
    chunk: dict[str, Any],
    qualification: dict[str, Any],
) -> dict[str, Any]:
    """Extract only decision-relevant source claims and verify their evidence."""
    max_claims = int(qualification.get("max_claims_per_chunk", 8))
    min_evidence_chars = int(qualification.get("min_evidence_chars", 24))
    eligible_categories = {
        str(value).casefold()
        for value in qualification.get("eligible_categories", DEFAULT_ELIGIBLE_CATEGORIES)
    }
    priority_candidates = _priority_rule_candidates(chunk["text"])
    prompt = f"""Identify source facts that a compact operational FoodEx2 wiki should preserve.

Return JSON only:
{{"claims":[{{"claim":"one atomic semantic fact","category":"operational|structural|exception|background|incidental","decision_axis":"base_term|facet|code_construction|validation|reporting|ontology_boundary|none","coverage_expectation":"required|optional|exclude","source_evidence":"one complete exact source sentence"}}]}}

Rules:
- `required` means omitting the fact could make two plausible FoodEx2 outputs differ: a
  different base term, facet, code string, validation result, reporting action, or
  interpretation of an ontology boundary. Set the matching `decision_axis`.
- Administrative process facts do NOT qualify: why maintenance occurred, when a report was
  published, how feedback was collected, or that terms were added/removed in general. A
  specific documented term/rule change can qualify only when the claim states the concrete
  coding consequence.
- A statement that unspecified terms, sections, or scope notes changed is background unless
  the source states the concrete term, boundary, or coder action affected.
- Use `operational` for actions/rules, `structural` for definitions or ontology boundaries, and `exception` for overrides to a general rule.
- Publication metadata, bibliography entries, footnote numbering, acknowledgements, wording trivia, and examples that establish no transferable rule are `incidental` and `exclude`.
- Background explanations that do not change a decision are `background` and `optional` or `exclude`.
- Examples may support a required claim only when they establish a general rule; state the transferable rule, not an example-recall fact.
- When evidence uses an example to demonstrate a broader rule, omit the example food and
  code from `claim`. State the general decision rule instead (for example: a
  non-nature-changing process belongs in a process facet, not a new base group).
- Each claim must state one rule only, in one concise sentence.
- Prefer near-extractive compression: every decision-bearing noun, status, condition, time,
  and consequence in the claim should appear in its evidence. Do not add inferred outcomes.
- `source_evidence` must be the shortest complete contiguous sentence that proves the claim,
  copied exactly from the supplied text. Never truncate evidence or join non-contiguous text.
- Return at most {max_claims} claims. Return an empty list if the chunk has no required operational knowledge.
- When the candidate list contains several independent required rules, use all available
  claim slots; do not stop after the first rule.

Mechanically surfaced rule-candidate sentences (prioritize them, but verify against the full chunk):
{json.dumps(priority_candidates, ensure_ascii=False)}

Source chunk {chunk['chunk_id']}:
{chunk['text']}
"""
    claim_schema = {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "maxItems": max_claims,
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["operational", "structural", "exception", "background", "incidental"],
                        },
                        "decision_axis": {
                            "type": "string",
                            "enum": [*sorted(DECISION_AXES), "none"],
                        },
                        "coverage_expectation": {
                            "type": "string",
                            "enum": ["required", "optional", "exclude"],
                        },
                        "source_evidence": {"type": "string"},
                    },
                    "required": [
                        "claim",
                        "category",
                        "decision_axis",
                        "coverage_expectation",
                        "source_evidence",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["claims"],
        "additionalProperties": False,
    }
    payload = model.generate_json(prompt, json_schema=claim_schema)
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        raise ValueError(f"qualifier returned no claims list for {chunk['chunk_id']}")
    extraction_claim_count = len(raw_claims)
    audit_claim_count = 0
    if qualification.get("completeness_audit", True):
        claimed_evidence_prefixes = []
        for raw in raw_claims:
            if not isinstance(raw, dict):
                continue
            evidence = str(raw.get("source_evidence") or "")
            evidence = re.split(r"(?:\.\.\.|…)", evidence, maxsplit=1)[0]
            normalized_evidence = _normalized_text(evidence)
            if len(normalized_evidence) >= 24:
                claimed_evidence_prefixes.append(normalized_evidence)
        audit_candidates = [
            candidate
            for candidate in priority_candidates
            if not any(
                prefix in _normalized_text(candidate)
                for prefix in claimed_evidence_prefixes
            )
        ]
        audit_prompt = f"""Audit an extraction of decision-relevant FoodEx2 source facts.

Return JSON only in the same claims schema:
{{"claims":[{{"claim":"one missed atomic fact","category":"operational|structural|exception","decision_axis":"base_term|facet|code_construction|validation|reporting|ontology_boundary","coverage_expectation":"required","source_evidence":"one complete exact source sentence"}}]}}

Find only REQUIRED operational rules, structural boundaries, or exceptions that the first
pass missed. A required fact must alter a concrete base-term, facet, code-construction,
validation, reporting, or ontology-boundary decision. General facts about maintenance,
publication, stakeholder feedback, or the existence of changes are background. Ignore
wording, citations, footnotes, publication metadata, background, and non-transferable
examples. Each claim must contain one rule. Evidence must be the shortest complete contiguous
source sentence, copied exactly and never truncated. Return an empty list when the first pass is complete.
Use all available claim slots when several independent required rules remain missing.
When a sentence uses an example to prove a broader rule, the claim must omit the example
food/code and state only the transferable rule.
Prefer near-extractive compression and do not introduce a status, condition, time, entity,
or consequence whose wording is absent from the evidence.

Unreviewed source sentences from chunk {chunk['chunk_id']}:
{json.dumps(audit_candidates, ensure_ascii=False)}
"""
        if audit_candidates:
            audit_payload = model.generate_json(audit_prompt, json_schema=claim_schema)
            audit_claims = audit_payload.get("claims")
            if not isinstance(audit_claims, list):
                raise ValueError(
                    f"qualification completeness audit returned no claims list for {chunk['chunk_id']}"
                )
        else:
            audit_claims = []
        audit_claim_count = len(audit_claims)
        raw_claims = [*raw_claims, *audit_claims]
    deduplicated_claims: list[Any] = []
    seen_claims: set[tuple[str, str]] = set()
    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue
        key = (
            _normalized_text(str(raw.get("claim") or "")),
            _normalized_text(str(raw.get("source_evidence") or "")),
        )
        if key in seen_claims:
            continue
        seen_claims.add(key)
        deduplicated_claims.append(raw)
    raw_claims = deduplicated_claims
    normalized_source = _normalized_text(chunk["text"])
    eligible: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    for raw in raw_claims[:max_claims]:
        if not isinstance(raw, dict):
            continue
        claim = str(raw.get("claim") or "").strip()
        category = str(raw.get("category") or "").casefold().strip()
        decision_axis = str(raw.get("decision_axis") or "").casefold().strip()
        expectation = str(raw.get("coverage_expectation") or "").casefold().strip()
        evidence = _complete_truncated_evidence(
            str(raw.get("source_evidence") or "").strip(), chunk["text"]
        )
        rationale = str(raw.get("rationale") or "").strip()
        item = {
            "claim": claim,
            "category": category,
            "decision_axis": decision_axis,
            "coverage_expectation": expectation,
            "source_evidence": evidence,
            "rationale": rationale,
        }
        reasons = []
        if not claim:
            reasons.append("empty_claim")
        if category not in eligible_categories:
            reasons.append("non_operational_category")
        if decision_axis not in DECISION_AXES:
            reasons.append("no_concrete_decision_axis")
        if expectation != "required":
            reasons.append("not_required")
        if len(evidence) < min_evidence_chars or _normalized_text(evidence) not in normalized_source:
            reasons.append("unverified_source_evidence")
        non_operational_reason = _non_operational_source_reason(claim, evidence)
        if non_operational_reason:
            reasons.append(non_operational_reason)
        if reasons:
            excluded.append({**item, "exclusion_reason": ",".join(reasons)})
        else:
            eligible.append(item)
    entailments = verify_claim_entailment(model, eligible)
    verified_eligible: list[dict[str, str]] = []
    for item, verification in zip(eligible, entailments, strict=True):
        item["entailment_rationale"] = str(verification.get("rationale") or "").strip()
        unsupported = verification.get("unsupported_additions")
        item["unsupported_additions"] = unsupported if isinstance(unsupported, list) else []
        lexical_unsupported = _unsupported_claim_terms(item["claim"], item["source_evidence"])
        item["unsupported_lexical_terms"] = lexical_unsupported
        if verification.get("entailed") is True and unsupported == [] and not lexical_unsupported:
            item["claim_grounding"] = "verified_paraphrase"
        else:
            item["original_claim"] = item["claim"]
            item["claim"] = item["source_evidence"]
            item["claim_grounding"] = "exact_source_evidence_fallback"
        non_operational_reason = _non_operational_source_reason(
            item["claim"], item["source_evidence"]
        )
        if non_operational_reason:
            excluded.append({**item, "exclusion_reason": non_operational_reason})
        else:
            verified_eligible.append(item)
    eligible = verified_eligible
    return {
        "chunk_id": chunk["chunk_id"],
        "eligible_claims": eligible,
        "excluded_claims": excluded,
        "raw_claim_count": len(raw_claims),
        "extraction_claim_count": extraction_claim_count,
        "audit_claim_count": audit_claim_count,
    }


def screen_question(
    model: LMStudioModel,
    *,
    question: str,
    claims: list[dict[str, str]],
) -> dict[str, Any]:
    """Reject quotation, citation, trivia, and non-transferable generated questions."""
    prompt = f"""Screen a generated FoodEx2 coverage question.

Return JSON only:
{{"decision_relevant":true,"answerable_from_claims":true,"quote_dependent":false,"decision_axis":"base_term|facet|code_construction|validation|reporting|ontology_boundary|none","relevant_claim_indexes":[0],"rationale":"name the two plausible outputs that could differ"}}

Accept only if answering the question could change a concrete base term, facet, code string,
validation result, reporting action, or interpretation of an ontology boundary. A question
about the purpose/history/process of maintenance or publication is NOT decision-relevant,
even when it is accurately answered by a qualified claim. Reject questions about wording,
page numbers, citations, publication metadata, footnotes, or recalling an example for its
own sake. Likewise reject historical "what term was added" recall and broad explanatory
questions about how the system collectively improves representation; rewrite-worthy facts
must instead be tested through a practical coding or reporting choice.

`quote_dependent` means the question requires verbatim wording, a citation, a page/table, or
other source-location recall. A question is NOT quote-dependent merely because its answer is
grounded in or can be paraphrased from the qualified claims. The question must be answerable
from the qualified claims without seeing the full source document. Set `decision_axis` to the
concrete choice tested, or `none` when rejecting. In the rationale, name the two plausible
FoodEx2 outputs or actions that answering the question would distinguish; if there are no two
plausible outputs, reject it. `relevant_claim_indexes` must contain only the zero-based indexes
of claims materially required to answer this question. Do not include merely adjacent facts
from the same source chunk.

Qualified claims:
{json.dumps([{"index": index, "claim": claim['claim']} for index, claim in enumerate(claims)], ensure_ascii=False)}

Question:
{question}
"""
    payload = model.generate_json(
        prompt,
        json_schema={
            "type": "object",
            "properties": {
                "decision_relevant": {"type": "boolean"},
                "answerable_from_claims": {"type": "boolean"},
                "quote_dependent": {"type": "boolean"},
                "decision_axis": {
                    "type": "string",
                    "enum": [*sorted(DECISION_AXES), "none"],
                },
                "relevant_claim_indexes": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0},
                },
                "rationale": {"type": "string", "maxLength": 400},
            },
            "required": [
                "decision_relevant",
                "answerable_from_claims",
                "quote_dependent",
                "decision_axis",
                "rationale",
            ],
            "additionalProperties": False,
        },
    )
    decision_relevant = payload.get("decision_relevant") is True
    answerable = payload.get("answerable_from_claims") is True
    quote_dependent = payload.get("quote_dependent") is True
    decision_axis = str(payload.get("decision_axis") or "").casefold().strip()
    relevant_claim_indexes = [
        index
        for index in payload.get("relevant_claim_indexes", range(len(claims)))
        if isinstance(index, int) and 0 <= index < len(claims)
    ]
    axis_inferred = False
    claim_axes = {
        str(claim.get("decision_axis") or "").casefold().strip()
        for claim in claims
        if str(claim.get("decision_axis") or "").casefold().strip() in DECISION_AXES
    }
    if decision_axis not in DECISION_AXES and len(claim_axes) == 1:
        decision_axis = next(iter(claim_axes))
        axis_inferred = True
    deterministic_quote_signal = bool(
        re.search(
            r"\b(?:page|footnote|citation|quote|according to)\b",
            question,
            re.I,
        )
    )
    administrative_topic = bool(
        re.search(
            r"\b(?:purpose|aim|objective|history|date|author|publisher|amendments?|"
            r"feedback|pilot projects?|maintenance window|total number|how many|"
            r"new terms?|scope notes?)\b",
            question,
            re.I,
        )
    )
    concrete_decision_language = bool(
        re.search(
            r"\b(?:base term|facet|code string|validat(?:e|ion)|raw commodity|"
            r"derivative|ontology boundary|classif(?:y|ication)|reporting action)\b",
            question,
            re.I,
        )
    )
    deterministic_administrative_signal = administrative_topic and not concrete_decision_language
    historical_recall_signal = bool(
        re.search(
            r"\b(?:what|which)\s+(?:new\s+)?(?:term|terms|descriptor|descriptors)\s+"
            r"(?:was|were|has been|have been)\s+(?:added|introduced|removed|updated)\b|"
            r"\bbased on a request from\b",
            question,
            re.I,
        )
    )
    broad_explanatory_signal = bool(
        re.search(
            r"^\s*how (?:do|does)\b.*\b(?:collectively|system(?:'s)? ability|"
            r"refine the system|organization of|relationship between)\b|"
            r"\bwhat (?:specific )?role do (?:these|the)\b",
            question,
            re.I,
        )
    )
    source_framed_signal = bool(
        re.search(
            r"\b(?:technical report|maintenance (?:in|during|of|report)|revision \d|"
            r"table \d+|table [A-Z]\d*|appendix [A-Z0-9]|based on a request from|"
            r"EFSA\s*\(?(?:19|20)\d{2}\)?|(?:19|20)\d{2} guidance|in the study)\b",
            question,
            re.I,
        )
    )
    procedure_inflation_signal = bool(
        re.search(
            r"\b(?:what steps should I follow|step[- ]by[- ]step|what is the procedure)\b",
            question,
            re.I,
        )
    )
    catalogue_recall_signal = bool(
        re.search(
            r"^\s*(?:what is|what are|which)\s+(?:the\s+)?(?:FoodEx2\s+)?"
            r"(?:code for|term for|new classification of|new facet descriptor for|"
            r"updated term|source commodity for|implicit (?:ingredient )?facet for|"
            r"two .* varieties|.* terms? (?:were )?(?:dismissed|added|removed|renamed))\b|"
            r"^\s*what (?:tea flavour )?terms? were dismissed\b",
            question,
            re.I,
        )
    )
    improvement_explanation_signal = bool(
        re.search(
            r"^\s*how (?:do|does)\b.*\b(?:improve|facilitate|enhance)\b.*"
            r"\b(?:mapping|representation|storage|retrieval|classification)\b",
            question,
            re.I,
        )
    )
    vague_reference_signal = bool(
        re.search(
            r"\b(?:this|these|those)\s+(?:missing|specific|detailed|food|product|code|term)|"
            r"\bthe missing (?:term|derivative|commodity|source)\b",
            question,
            re.I,
        )
    )
    rationale = str(payload.get("rationale") or "").strip()
    self_contradicting_rationale = bool(
        re.search(
            r"\b(?:not enough|do not contain enough|does not contain enough|insufficient|"
            r"cannot (?:answer|determine)|can't (?:answer|determine)|not specific enough|"
            r"lacks? (?:enough|the required|specific))\b",
            rationale,
            re.I,
        )
    )
    asks_for_exact_code = bool(
        re.search(r"\b(?:what|which)\s+(?:is\s+the\s+)?(?:foodex2\s+)?code\b", question, re.I)
    )
    claims_supply_code = any(
        re.search(r"\b(?:A[0-9A-Z]{4}|F\d{2}(?:\.[A0-9]+)?)\b", str(claim.get("claim") or ""))
        for claim in claims
    )
    unsupported_exact_code_request = asks_for_exact_code and not claims_supply_code
    return {
        "accepted": decision_relevant
        and answerable
        and decision_axis in DECISION_AXES
        and not quote_dependent
        and not deterministic_quote_signal
        and not deterministic_administrative_signal
        and not historical_recall_signal
        and not broad_explanatory_signal
        and not source_framed_signal
        and not procedure_inflation_signal
        and not catalogue_recall_signal
        and not improvement_explanation_signal
        and not vague_reference_signal
        and not self_contradicting_rationale
        and not unsupported_exact_code_request,
        "decision_relevant": decision_relevant,
        "answerable_from_claims": answerable,
        "quote_dependent": quote_dependent or deterministic_quote_signal,
        "decision_axis": decision_axis,
        "decision_axis_inferred_from_claims": axis_inferred,
        "administrative_only": deterministic_administrative_signal,
        "historical_recall": historical_recall_signal,
        "broad_explanatory": broad_explanatory_signal,
        "source_framed": source_framed_signal,
        "procedure_inflation": procedure_inflation_signal,
        "catalogue_recall": catalogue_recall_signal,
        "improvement_explanation": improvement_explanation_signal,
        "vague_reference": vague_reference_signal,
        "self_contradicting_rationale": self_contradicting_rationale,
        "unsupported_exact_code_request": unsupported_exact_code_request,
        "relevant_claim_indexes": relevant_claim_indexes,
        "rationale": rationale,
    }


def _question_id(chunk_id: str, question: str) -> str:
    digest = hashlib.sha256(f"{chunk_id}\n{question.strip()}".encode("utf-8")).hexdigest()
    return f"COV-{digest[:16].upper()}"


def _weighted_style_plan(
    configured: dict[str, Any],
    *,
    question_count: int,
    styles_per_question: int,
    claim_count: int,
    seed: int,
) -> list[list[str]]:
    """Choose transparent prompt styles deterministically from configured weights."""
    weights: dict[str, float] = {}
    for raw_name, raw_weight in configured.items():
        name = QUESTION_STYLE_ALIASES.get(str(raw_name).casefold())
        if name is None:
            raise ValueError(f"unsupported question style: {raw_name}")
        weight = float(raw_weight)
        if weight < 0:
            raise ValueError("question style weights cannot be negative")
        if weight == 0:
            continue
        if name == "multi-hop" and claim_count < 2:
            continue
        weights[name] = weights.get(name, 0.0) + weight
    if not weights or sum(weights.values()) <= 0:
        weights = {"reasoning": 1.0}
    rng = random.Random(seed)
    plan: list[list[str]] = []
    for _ in range(question_count):
        available = dict(weights)
        selected: list[str] = []
        for _ in range(min(max(0, styles_per_question), len(available))):
            names = list(available)
            choice = rng.choices(names, weights=[available[name] for name in names], k=1)[0]
            selected.append(choice)
            del available[choice]
        plan.append(selected or ["reasoning"])
    return plan


def generate_questions(
    model: LMStudioModel,
    *,
    claims: list[dict[str, str]],
    question_count: int,
    configured_styles: dict[str, Any],
    styles_per_question: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Generate source-grounded questions directly through LM Studio structured JSON."""
    if question_count < 1:
        raise ValueError("questions_per_chunk must be at least one")
    plan = _weighted_style_plan(
        configured_styles,
        question_count=question_count,
        styles_per_question=styles_per_question,
        claim_count=len(claims),
        seed=seed,
    )
    requests = [
        {
            "index": index,
            "styles": styles,
            "style_guidance": [QUESTION_STYLE_GUIDANCE[style] for style in styles],
        }
        for index, styles in enumerate(plan)
    ]
    prompt = f"""Write exactly {question_count} source-driven FoodEx2 coverage questions.

Return JSON only:
{{"questions":[{{"index":0,"question":"one concise self-contained question"}}]}}

Each question must test a practical choice that a compact operational wiki should enable:
base-term selection, facet use, code construction, validation, reporting, or an ontology
boundary. Use only the supplied claims. Do not invent food examples, catalogue terms, codes,
exceptions, or facts. Do not ask for quotations, citations, page/table numbers, source history,
publication facts, or what a document says. Do not mention EFSA, a guideline, source, chunk,
claim, or page. Phrase the question as a real coding or reporting decision. If a requested
style cannot be supported by the claims, use straightforward reasoning instead of fabricating
details. Keep each question short and independently answerable.

Qualified claims:
{json.dumps([claim["claim"] for claim in claims], ensure_ascii=False)}

Requested question styles:
{json.dumps(requests, ensure_ascii=False)}
"""
    payload = model.generate_json(
        prompt,
        json_schema={
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "minItems": question_count,
                    "maxItems": question_count,
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer", "minimum": 0},
                            "question": {"type": "string", "minLength": 8, "maxLength": 500},
                        },
                        "required": ["index", "question"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["questions"],
            "additionalProperties": False,
        },
    )
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list) or len(raw_questions) != question_count:
        raise ValueError("local generator did not return the requested number of questions")
    by_index = {
        item.get("index"): item
        for item in raw_questions
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }
    if set(by_index) != set(range(question_count)):
        raise ValueError("local generator did not return every question index exactly once")
    generated = []
    seen: set[str] = set()
    for index in range(question_count):
        question = str(by_index[index].get("question") or "").strip()
        normalized = _normalized_text(question)
        if len(question) < 8 or normalized in seen:
            raise ValueError("local generator returned an empty or duplicate question")
        seen.add(normalized)
        generated.append({"question": question, "question_styles": plan[index]})
    return generated


def _generation_checkpoint(
    *,
    testset_id: str,
    chunks: list[dict[str, Any]],
    generation: dict[str, Any],
    qualification: dict[str, Any],
    generator_model: dict[str, Any],
    run_models: dict[str, dict[str, Any]],
) -> tuple[Path, dict[str, Any]]:
    signature_payload = {
        "pipeline_version": GENERATION_PIPELINE_VERSION,
        "testset_id": testset_id,
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "text_sha256": hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest(),
            }
            for chunk in chunks
        ],
        "generation": generation,
        "qualification": qualification,
        "generator_model": generator_model,
        "run_models": run_models,
    }
    signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    path = REPO_ROOT / "evals" / "coverage" / "reports" / "checkpoints" / f"{testset_id}.json"
    checkpoint: dict[str, Any] = {
        "signature": signature,
        "qualifications": {},
        "generated": {},
    }
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(existing, dict) and existing.get("signature") == signature:
            checkpoint = existing
    return path, checkpoint


def generate_testset(
    config_path: Path,
    *,
    output: Path,
    manifest_output: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if output.exists() and not force:
        raise FileExistsError(f"{output} already exists; use --force only for deliberate regeneration")
    config = load_yaml(config_path)
    testset_id = str(config.get("testset_id") or output.stem)
    manifest_output = manifest_output or (
        Path(__file__).parent / "config" / f"{testset_id}.yaml"
    )
    if manifest_output.exists() and not force:
        raise FileExistsError(
            f"{manifest_output} already exists; version the testset or use --force deliberately"
        )
    manifest_path = repo_path(config.get("source_manifest", DEFAULT_MANIFEST))
    manifest_sources = load_manifest(manifest_path)
    source_ids = set(config.get("source_ids") or [source["id"] for source in manifest_sources])
    generation = config.get("generation") or {}
    max_chars = int(generation.get("chunk_max_chars", 6000))
    chunks_payload = chunk_sources(manifest_path, max_chars=max_chars, source_ids=source_ids)
    chunks = chunks_payload["chunks"]
    configured_chunk_ids = [str(value) for value in generation.get("chunk_ids", [])]
    if configured_chunk_ids:
        chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
        missing_chunk_ids = [value for value in configured_chunk_ids if value not in chunks_by_id]
        if missing_chunk_ids:
            raise ValueError(f"configured chunk_ids were not found: {missing_chunk_ids}")
        chunks = [chunks_by_id[value] for value in configured_chunk_ids]
    limit = generation.get("max_chunks")
    if limit is not None:
        chunks = chunks[: int(limit)]
    if not chunks:
        raise ValueError("no authoritative source chunks were selected")

    generator_config = local_model_config(config.get("models", {}).get("generator", {}))
    default_run_models = {
        role: local_model_config(config.get("models", {}).get(role, {}))
        for role in ("selector", "answerer", "judge")
    }
    model = LMStudioModel(
        model=generator_config["model"],
        base_url=generator_config["base_url"],
        api_key_env=generator_config.get("api_key_env"),
        temperature=float(generator_config.get("temperature", 0.0)),
        seed=int(generator_config.get("seed", 42)),
        max_tokens=int(generator_config.get("max_tokens", 2048)),
        timeout=float(generator_config.get("timeout_seconds", 180)),
        max_retries=int(generator_config.get("max_retries", 3)),
    )
    qualification_config = config.get("qualification") or {}
    qualification_model_config = local_model_config(
        config.get("models", {}).get("qualifier")
        or config.get("models", {}).get("generator", {})
    )
    qualification_model = LMStudioModel(
        model=qualification_model_config["model"],
        base_url=qualification_model_config["base_url"],
        api_key_env=qualification_model_config.get("api_key_env"),
        temperature=float(qualification_model_config.get("temperature", 0.0)),
        seed=int(qualification_model_config.get("seed", 42)),
        max_tokens=int(qualification_config.get("max_tokens", 4096)),
        timeout=float(qualification_model_config.get("timeout_seconds", 180)),
        max_retries=int(qualification_model_config.get("max_retries", 3)),
    )
    checkpoint_path, checkpoint = _generation_checkpoint(
        testset_id=testset_id,
        chunks=chunks,
        generation=generation,
        qualification=qualification_config,
        generator_model=generator_config,
        run_models=default_run_models,
    )
    cached_qualifications = checkpoint.setdefault("qualifications", {})
    qualification_results = []
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        result = cached_qualifications.get(chunk_id)
        if not isinstance(result, dict):
            result = qualify_chunk(qualification_model, chunk, qualification_config)
            cached_qualifications[chunk_id] = result
            write_json(checkpoint_path, checkpoint)
        qualification_results.append(result)
    qualification_by_chunk = {
        result["chunk_id"]: result for result in qualification_results
    }
    eligible_chunks = [
        chunk
        for chunk in chunks
        if qualification_by_chunk[chunk["chunk_id"]]["eligible_claims"]
    ]
    if not eligible_chunks:
        raise ValueError("automated qualification found no decision-relevant source claims")
    configured_styles = generation.get("question_styles") or generation.get("evolutions") or {
        "reasoning": 0.25,
        "multi-hop": 0.25,
        "concretising": 0.25,
        "comparative": 0.25,
    }
    styles_per_question = int(
        generation.get("styles_per_question", generation.get("num_evolutions", 1))
    )
    # Validate style names and weights before making any generation calls.
    _weighted_style_plan(
        configured_styles,
        question_count=1,
        styles_per_question=styles_per_question,
        claim_count=2,
        seed=int(generator_config.get("seed", 42)),
    )
    cases: list[dict[str, Any]] = []
    rejected_questions: list[dict[str, Any]] = []
    generated_checkpoint = checkpoint.setdefault("generated", {})
    base_seed = int(generator_config.get("seed", 42))
    for parent in eligible_chunks:
        parent_id = parent["chunk_id"]
        cached_generation = generated_checkpoint.get(parent_id)
        if isinstance(cached_generation, dict):
            cases.extend(cached_generation.get("cases") or [])
            rejected_questions.extend(cached_generation.get("rejected_questions") or [])
            continue
        claims = qualification_by_chunk[parent_id]["eligible_claims"]
        chunk_seed = int(
            hashlib.sha256(f"{base_seed}:{parent_id}".encode("utf-8")).hexdigest()[:8], 16
        )
        generated_questions = generate_questions(
            model,
            claims=claims,
            question_count=int(generation.get("questions_per_chunk", 1)),
            configured_styles=configured_styles,
            styles_per_question=styles_per_question,
            seed=chunk_seed,
        )
        chunk_cases: list[dict[str, Any]] = []
        chunk_rejections: list[dict[str, Any]] = []
        for generated in generated_questions:
            question = generated["question"]
            screening = screen_question(
                qualification_model, question=question, claims=claims
            )
            if not screening["accepted"]:
                chunk_rejections.append(
                    {
                        "chunk_id": parent_id,
                        "question": question,
                        "screening": screening,
                    }
                )
                continue
            chunk_cases.append(
                {
                    "id": _question_id(parent_id, question),
                    "question": question,
                    "source_id": parent["source_id"],
                    "chunk_id": parent_id,
                    "page_start": parent.get("page_start"),
                    "page_end": parent.get("page_end"),
                    "section": parent.get("section"),
                    "question_styles": generated["question_styles"],
                    "qualified_claims": claims,
                    "automated_screening": screening,
                }
            )
        generated_checkpoint[parent_id] = {
            "cases": chunk_cases,
            "rejected_questions": chunk_rejections,
        }
        write_json(checkpoint_path, checkpoint)
        cases.extend(chunk_cases)
        rejected_questions.extend(chunk_rejections)
    if not cases:
        raise ValueError("automated screening rejected every generated question")
    selected_sources = [source for source in manifest_sources if source["id"] in source_ids]
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    frozen_manifest = {
        "version": 1,
        "testset_id": testset_id,
        "generation_date": generated_at,
        "source_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "sources": [
            {
                "id": source["id"],
                "version": source.get("version"),
                "sha256": source.get("sha256"),
            }
            for source in selected_sources
        ],
        "generator": {
            "provider": "lmstudio",
            "backend": "direct_structured_json",
            "model": generator_config["model"],
            "base_url": generator_config["base_url"],
            "temperature": generator_config.get("temperature", 0.0),
            "seed": generator_config.get("seed", 42),
            "questions_per_chunk": generation.get("questions_per_chunk", 1),
            "chunk_max_chars": max_chars,
            "chunk_ids": configured_chunk_ids,
            "max_chunks": limit,
            "question_styles": configured_styles,
            "styles_per_question": styles_per_question,
        },
        "qualification": {
            "model": qualification_model_config["model"],
            "eligible_categories": sorted(
                qualification_config.get("eligible_categories", DEFAULT_ELIGIBLE_CATEGORIES)
            ),
            "max_claims_per_chunk": qualification_config.get("max_claims_per_chunk", 8),
            "min_evidence_chars": qualification_config.get("min_evidence_chars", 24),
            "completeness_audit": qualification_config.get("completeness_audit", True),
            "require_exact_source_evidence": True,
            "automated_question_screening": True,
            "human_review_required": False,
        },
        "retrieval": config.get("retrieval") or {},
        "models": {
            **default_run_models,
            "escalation_judge": config.get("models", {}).get("escalation_judge"),
        },
    }
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_text(
        yaml.safe_dump(frozen_manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    payload = {
        "version": 1,
        "testset_id": testset_id,
        "generated_at": generated_at,
        "config_manifest": str(manifest_output.resolve().relative_to(REPO_ROOT)),
        "source_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "sources": frozen_manifest["sources"],
        "generator": frozen_manifest["generator"],
        "default_run_models": default_run_models,
        "qualification_summary": {
            "source_chunk_count": len(chunks),
            "eligible_chunk_count": len(eligible_chunks),
            "excluded_chunk_count": len(chunks) - len(eligible_chunks),
            "accepted_question_count": len(cases),
            "rejected_question_count": len(rejected_questions),
        },
        "qualification_audit": [
            {
                "chunk_id": result["chunk_id"],
                "raw_claim_count": result["raw_claim_count"],
                "extraction_claim_count": result["extraction_claim_count"],
                "audit_claim_count": result["audit_claim_count"],
                "eligible_claim_count": len(result["eligible_claims"]),
                "excluded_claims": result["excluded_claims"],
            }
            for result in qualification_results
        ],
        "rejected_questions": rejected_questions,
        "case_count": len(cases),
        "cases": cases,
    }
    write_json(output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    payload = generate_testset(
        args.config.resolve(),
        output=args.output.resolve(),
        manifest_output=args.manifest_output.resolve() if args.manifest_output else None,
        force=args.force,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "config_manifest": payload["config_manifest"],
                "case_count": payload["case_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
