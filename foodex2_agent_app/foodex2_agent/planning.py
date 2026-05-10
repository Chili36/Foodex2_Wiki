from __future__ import annotations

from dataclasses import dataclass


DERIVATIVE_WORDS = {
    "cheese",
    "wine",
    "beer",
    "flour",
    "oil",
    "juice",
    "sauce",
    "powder",
    "extract",
    "concentrate",
    "vinegar",
    "yoghurt",
    "yogurt",
}

COMPOSITE_WORDS = {
    "meal",
    "dish",
    "salad",
    "sandwich",
    "soup",
    "cake",
    "pie",
    "pizza",
    "stew",
    "with",
}

PROCESS_WORDS = {
    "rennet",
    "coagulat",
    "ferment",
    "ripen",
    "cured",
    "uncured",
    "pasteuris",
    "sterilis",
    "canned",
    "dried",
    "smoked",
    "brined",
    "marinated",
}

QUALITY_WORDS = {
    "fat",
    "sugar",
    "alcohol",
    "lactose",
    "organic",
    "free",
    "%",
}


@dataclass(frozen=True)
class SourcePlan:
    food_type_hypothesis: str
    base_concept_query: str
    semantic_query: str
    targeted_facet_queries: list[str]
    probably_implicit_or_non_coding: list[str]
    tool_strategy: list[dict[str, str]]
    search_budget: dict[str, object]
    decision_checklist: list[str]
    stopping_rule: str


def plan_source_text(text: str) -> dict[str, object]:
    normalized = " ".join(text.replace(",", " ").replace(".", " ").split())
    lower = normalized.lower()
    tokens = lower.split()

    food_type = "raw commodity"
    if any(word in lower for word in DERIVATIVE_WORDS):
        food_type = "derivative"
    if any(word in lower for word in COMPOSITE_WORDS) and "cheese" not in lower:
        food_type = "composite"

    base_query = _base_query(lower, tokens)
    facet_queries = _targeted_facet_queries(lower)
    implicit = _probably_implicit(lower)

    plan = SourcePlan(
        food_type_hypothesis=food_type,
        base_concept_query=base_query,
        semantic_query=normalized,
        targeted_facet_queries=facet_queries,
        probably_implicit_or_non_coding=implicit,
        tool_strategy=[
            {
                "phase": "1 orient",
                "tools": "plan_foodex2_coding_strategy, wiki_ask_guidance",
                "exit": "Food type, likely base concept, and coding risks are known.",
            },
            {
                "phase": "2 recall base candidates",
                "tools": "semantic_search_candidates, optionally one catalogue label search",
                "exit": "Two or three plausible reportable base candidates are identified.",
            },
            {
                "phase": "3 inspect and choose base",
                "tools": "catalog_get_term, catalog_get_implicit_facets",
                "exit": "Best base term and rejected alternatives are explainable from scope notes or implicit facets.",
            },
            {
                "phase": "4 draft and validate",
                "tools": "validator_validate_code",
                "exit": "A legal draft exists, or a hard validator issue tells you exactly what to fix.",
            },
            {
                "phase": "5 targeted refinements only",
                "tools": "catalog_search_facets or catalogue term search only for one source-critical unresolved fact",
                "exit": "Each meaningful source fact is covered, unsupported, ambiguous, or explicitly not coded.",
            },
        ],
        search_budget={
            "wikiAskGuidance": 1,
            "semanticCandidateSearches": 1,
            "catalogueLabelSearches": "0-1 unless semantic recall clearly missed the base concept",
            "candidateInspections": "2-3 maximum unless validator gives a hard reason",
            "facetSearchesPerUnresolvedFact": 1,
            "afterCall10": "draft, validate, or finalize; do not broaden search",
        },
        decision_checklist=[
            "Decide food type before searching for facets.",
            "Before each tool call, state what answer it is expected to provide and whether that answer could change the constructed code.",
            "Use semantic search to recall plausible base terms, then inspect only the best reportable base candidates.",
            "Validate the base-only draft as soon as a plausible base term is inspected.",
            "Search facets only for explicit details that are not already implicit in the inspected base term.",
            "Do not keep searching for a facet after one targeted query fails; record the detail as not coded.",
        ],
        stopping_rule=(
            "After a plausible base term is inspected and validator accepts a draft, stop searching unless "
            "there is one exact unresolved detail with a likely facet query."
        ),
    )
    return {
        "foodTypeHypothesis": plan.food_type_hypothesis,
        "baseConceptQuery": plan.base_concept_query,
        "semanticQuery": plan.semantic_query,
        "targetedFacetQueries": plan.targeted_facet_queries,
        "probablyImplicitOrNonCoding": plan.probably_implicit_or_non_coding,
        "toolStrategy": plan.tool_strategy,
        "searchBudget": plan.search_budget,
        "decisionChecklist": plan.decision_checklist,
        "stoppingRule": plan.stopping_rule,
    }


def _base_query(lower: str, tokens: list[str]) -> str:
    if "fresh" in tokens and "cheese" in tokens:
        return "fresh uncured cheese"
    for word in DERIVATIVE_WORDS:
        if word in lower:
            modifiers = [token for token in tokens if token in {"fresh", "uncured", "ripened", "brined"}]
            return " ".join([*modifiers, word]).strip()
    return " ".join(tokens[:5])


def _targeted_facet_queries(lower: str) -> list[str]:
    queries: list[str] = []
    if "%" in lower and "fat" in lower:
        number = _number_before_percent(lower)
        queries.append(f"{number} % fat" if number else "fat")
    elif "fat" in lower:
        queries.append("fat")
    if "alcohol-free" in lower or "alcohol free" in lower:
        queries.append("alcohol free")
    if "sugar free" in lower or "sugar-free" in lower:
        queries.append("sugar free")
    return queries[:3]


def _probably_implicit(lower: str) -> list[str]:
    values: list[str] = []
    if "rennet" in lower or "coagulat" in lower:
        values.append("rennet/coagulation is usually part of cheesemaking; verify against the chosen cheese base before searching more facets")
    if "milk" in lower and "cheese" in lower:
        values.append("milk origin may be implicit in a cheese derivative base unless a narrower species is given")
    if "fresh" in lower and "cheese" in lower:
        values.append("fresh/unripened state may be implicit in a fresh cheese base")
    return values


def _number_before_percent(lower: str) -> str | None:
    before = lower.split("%", 1)[0].strip().split()
    if not before:
        return None
    token = before[-1]
    return token if token.replace(".", "", 1).isdigit() else None
