from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .librarian import PageSelectionResult


RUNTIME_RULES_PAGE_NAME = "RUNTIME_RULES.md"
BASE_TERM_PAGE = "base-term-selection.md"
IMPLICIT_EXPLICIT_PAGE = "implicit-vs-explicit-facets.md"
TERM_TYPE_PAGE = "term-type-facet-constraints.md"
PROCESS_PAGE = "process-facets.md"
PROCESS_VALIDATION_PAGE = "process-validation-rules.md"
INGREDIENT_PAGE = "ingredient-facets.md"
PACKAGING_PAGE = "packaging-facets.md"
CHEMMON_PAGE = "chemical-monitoring-foodex2.md"
DOMAIN_PAGE = "domain-specific-validation.md"

PROCESS_KEYWORDS = {
    "dried",
    "drying",
    "dehydrated",
    "pickled",
    "pickling",
    "marinated",
    "fermented",
    "canned",
    "jarred",
    "smoked",
    "fried",
    "boiled",
    "roasted",
    "cooked",
    "baked",
    "grilled",
    "frozen",
    "chilled",
    "powder",
    "powdered",
    "juice",
    "flour",
}
PACKAGING_KEYWORDS = {
    "jar",
    "glass",
    "bottle",
    "can",
    "boxed",
    "carton",
    "pack",
    "packaged",
    "tin",
    "plastic",
}
INGREDIENT_KEYWORDS = {
    "with",
    "containing",
    "contains",
    "flavoured",
    "flavored",
    "flavour",
    "flavor",
    "ingredient",
    "sauce",
    "salad",
    "pizza",
    "risotto",
    "yogurt",
    "yoghurt",
}
DOMAIN_KEYWORDS = {
    "chemmon": [CHEMMON_PAGE, DOMAIN_PAGE],
    "vmpr": [CHEMMON_PAGE, DOMAIN_PAGE],
    "vetdrug": [CHEMMON_PAGE, DOMAIN_PAGE],
    "additive": [DOMAIN_PAGE],
    "additives": [DOMAIN_PAGE],
    "acrylamide": [DOMAIN_PAGE],
    "infant": [DOMAIN_PAGE],
    "baby": [DOMAIN_PAGE],
}


def _flatten_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for item in value.values():
            flattened.extend(_flatten_strings(item))
        return flattened
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten_strings(item))
        return flattened
    return []


def _component_kinds(payload: dict[str, Any]) -> set[str]:
    raw_components = payload.get("deconstructed_query", {}).get("components", [])
    kinds: set[str] = set()
    if not isinstance(raw_components, list):
        return kinds
    for component in raw_components:
        if isinstance(component, dict):
            kind = component.get("kind")
            if isinstance(kind, str):
                kinds.add(kind.upper())
    return kinds


def _candidate_term_types(payload: dict[str, Any]) -> set[str]:
    term_types: set[str] = set()
    for candidate in payload.get("candidates", []):
        if isinstance(candidate, dict):
            term_type = candidate.get("termType")
            if isinstance(term_type, str) and term_type:
                term_types.add(term_type.lower())
    return term_types


def _text_corpus(payload: dict[str, Any]) -> str:
    pieces: list[str] = []
    for section in (
        payload.get("search_term"),
        payload.get("deconstructed_query"),
        payload.get("context"),
    ):
        pieces.extend(_flatten_strings(section))
    return " ".join(piece.lower() for piece in pieces if piece).strip()


def _has_any_keyword(corpus: str, keywords: set[str]) -> bool:
    return any(keyword in corpus for keyword in keywords)


@dataclass(frozen=True)
class DeterministicSelection:
    pages_used: list[str]
    tool_trace: list[dict[str, Any]]


def _select_pages(payload: dict[str, Any], *, max_pages: int) -> DeterministicSelection:
    term_types = _candidate_term_types(payload)
    component_kinds = _component_kinds(payload)
    corpus = _text_corpus(payload)

    has_process_signal = "PROCESS" in component_kinds or _has_any_keyword(corpus, PROCESS_KEYWORDS)
    has_packaging_signal = "PACKAGING" in component_kinds or _has_any_keyword(
        corpus, PACKAGING_KEYWORDS
    )
    has_ingredient_signal = (
        {"INGREDIENT", "FLAVOUR", "FLAVOR"} & component_kinds
        or _has_any_keyword(corpus, INGREDIENT_KEYWORDS)
    )
    has_composite_signal = bool({"c", "s"} & term_types)
    has_raw_derivative_mix = "r" in term_types and "d" in term_types
    has_constraint_signal = bool({"f", "h", "g"} & term_types) or len(term_types) > 1

    selected: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(page_name: str, rule_id: str, reason: str) -> None:
        if page_name in seen or len(selected) >= max_pages:
            return
        seen.add(page_name)
        selected.append((page_name, rule_id, reason))

    add(RUNTIME_RULES_PAGE_NAME, "ALWAYS", "Always attach compact runtime rules for prompt packing.")
    add(BASE_TERM_PAGE, "CORE_BASE", "Base-term selection is the default support page for coding cases.")

    if has_process_signal:
        add(PROCESS_PAGE, "SIG_PROCESS", "Processing signal detected from components or query wording.")
    if has_process_signal or has_raw_derivative_mix:
        add(
            PROCESS_VALIDATION_PAGE,
            "SIG_PROCESS_VALIDATE",
            "Process or raw-vs-derivative signal detected; process boundaries may matter.",
        )
    if has_ingredient_signal or has_composite_signal:
        add(
            INGREDIENT_PAGE,
            "SIG_INGREDIENT",
            "Ingredient or composite signal detected from candidate types or query wording.",
        )
    if has_packaging_signal:
        add(
            PACKAGING_PAGE,
            "SIG_PACKAGING",
            "Packaging signal detected from components or query wording.",
        )
    if has_constraint_signal or has_raw_derivative_mix or has_composite_signal:
        add(
            TERM_TYPE_PAGE,
            "SIG_TERMTYPE",
            "Mixed candidate term types or facet/hierarchy candidates detected.",
        )
    if has_process_signal or has_ingredient_signal or has_composite_signal or has_raw_derivative_mix:
        add(
            IMPLICIT_EXPLICIT_PAGE,
            "SIG_IMPLICIT",
            "Implicit-vs-explicit facet boundary likely matters for this case.",
        )

    for keyword, pages in DOMAIN_KEYWORDS.items():
        if keyword in corpus:
            for page_name in pages:
                add(
                    page_name,
                    f"SIG_DOMAIN_{keyword.upper()}",
                    f"Domain marker '{keyword}' detected in query, context, or candidate text.",
                )

    tool_trace = [
        {
            "page_name": page_name,
            "order": idx,
            "reason": reason,
            "rule_id": rule_id,
            "synthetic": False,
        }
        for idx, (page_name, rule_id, reason) in enumerate(selected, start=1)
    ]
    return DeterministicSelection(
        pages_used=[page_name for page_name, _rule_id, _reason in selected],
        tool_trace=tool_trace,
    )


class DeterministicContextSelector:
    def __init__(self, *, max_pages: int = 6):
        self.max_pages = max_pages
        self.model = "deterministic-context-selector"

    def run(self, payload: dict[str, Any]) -> PageSelectionResult:
        selector_started = time.perf_counter()
        selection = _select_pages(payload, max_pages=self.max_pages)
        return PageSelectionResult(
            pages_used=selection.pages_used,
            tool_trace=selection.tool_trace,
            token_summary={
                "model": self.model,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tracked_tokens": 0,
                "per_call": [],
            },
            timing_summary={
                "calls": 0,
                "llm_time_ms": 0,
                "selector_wall_time_ms": int((time.perf_counter() - selector_started) * 1000),
                "per_call": [],
            },
        )
