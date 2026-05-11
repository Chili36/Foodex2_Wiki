from __future__ import annotations

from pathlib import Path

from .settings import APP_DIR


AGENT_MD_PATH = APP_DIR / "AGENT.md"


RUNTIME_CONTRACT = """## Runtime Tool And Output Contract

You have FOUR tools. Use them in this order:

1. `semantic_search_candidates(query, limit)` — call first to get candidate base codes from Qdrant. If the first pass misses, refine the query (synonyms, food-type words, language-translated form) and call once more.
2. `catalog_get_term(code)` — inspect the best 1-2 candidates. Returns name, term type, scope note, hierarchies, and implicit facets in one call. Do not re-fetch the same code.
3. `validator_validate_code(code, domain, context)` — validate a draft as soon as you have a plausible base. Clean validation is the gate to finalize. Hard warnings drive ONE targeted repair. Soft warnings are advisory — do not chase them.
4. `catalog_search_facets(query, facet_type, limit)` — only for a source-critical explicit facet not already covered by the chosen base's implicit facets. One targeted call per missing fact. Empty result means classify the fact as not_codeable and move on.

Discipline:

- Use only the provided tools. Do not use FoodEx2 facts from memory.
- Every tool call requires a `tool_rationale` audit object stating the source fact, expected answer, whether it can change the code, and the fallback if no useful result.
- Return final JSON only after the validator has been called at least once and accepted the constructed code, or the validator has produced a hard warning you have already addressed once.
- After validation accepts the code, only call further tools to resolve a SPECIFIC named source fact that is still uncovered. Do not re-validate the same code or re-search the same concept.
- `confidence` must be an integer from 1 to 5. Never return a decimal probability such as 0.9 or a percentage such as 90.

Final JSON shape:
{
  "selectedCode": "base code",
  "selectedName": "base name",
  "selectedTermType": "r|d|c|s|h|g|f|n",
  "constructedCode": "complete FoodEx2 code",
  "reasoning": "concise audit reasoning with tool-backed facts",
  "implicitFacets": [],
  "explicitFacets": [],
  "suggestedExplicitFacets": [],
  "factCoverage": [
    {"fact": "source fact", "disposition": "implicit_in_base|refinement|explicit_facet|not_codeable|domain_inactive|contradicts_base|uncertain", "evidence": "short tool-grounded reason"}
  ],
  "validationCheck": {
    "passes": true,
    "warnings": []
  },
  "alternativeCodes": [
    {"code": "...", "name": "...", "reason": "..."}
  ],
  "confidence": 4
}
"""


DEBUG_TOOL_WHY_CONTRACT = """## Debug Tool Why

Every tool call includes a required `why` string in this debug run. Keep it under 160 characters and state the expected answer, source fact, and fallback if empty. This is a visible audit note, not hidden chain-of-thought.
"""


SHORT_INSTRUCTIONS = (
    "You are a FoodEx2 coding analyst. The developer-role message at the start "
    "of this conversation contains your full strategy (AGENT.md and the runtime "
    "tool/output contract); it stays in scope across every tool round, so do not "
    "re-derive it. Always emit a `tool_rationale` per the schema on every tool "
    "call. Return the final JSON only after calling validator_validate_code at "
    "least once; `confidence` must be an integer from 1 to 5."
)


def load_agent_markdown(path: Path = AGENT_MD_PATH) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_short_instructions() -> str:
    """Stable, tiny system-prompt preamble passed via the API `instructions` slot.

    The full AGENT.md + runtime contract lives in the conversation history as a
    developer-role message (see `build_developer_preamble`) so it is paid for
    once per agent run rather than re-sent on every tool-round continuation.
    """
    return SHORT_INSTRUCTIONS


def build_developer_preamble(
    path: Path = AGENT_MD_PATH,
    *,
    include_debug_tool_why: bool = False,
) -> str:
    """Full AGENT.md + runtime contract, sent once as the round-0 developer message."""
    agent_markdown = load_agent_markdown(path)
    parts = [agent_markdown, RUNTIME_CONTRACT.strip()]
    if include_debug_tool_why:
        parts.append(DEBUG_TOOL_WHY_CONTRACT.strip())
    return "\n\n".join(parts) + "\n"


def build_agent_instructions(
    path: Path = AGENT_MD_PATH,
    *,
    include_debug_tool_why: bool = False,
) -> str:
    """Deprecated combined builder, kept for back-compat with older callers/tests.

    New code should call `build_short_instructions()` (for the API `instructions`
    slot) and `build_developer_preamble()` (for the first developer message)
    separately.
    """
    return build_developer_preamble(path, include_debug_tool_why=include_debug_tool_why)


def build_user_task(search_term: str, *, language_hint: str | None, domain: str | None) -> str:
    parts = [
        "Code this FoodEx2 matrix using the catalogue, wiki, and validator tools.",
        "Start by planning the coding strategy, not by searching for facets.",
        f"Search term: {search_term}",
    ]
    if language_hint:
        parts.append(f"Language hint: {language_hint}")
    if domain:
        parts.append(f"Reporting domain: {domain}")
    else:
        parts.append("Reporting domain: not specified; do not infer a domain.")
    return "\n".join(parts)
