from __future__ import annotations

from pathlib import Path

from .settings import APP_DIR


AGENT_MD_PATH = APP_DIR / "AGENT.md"


RUNTIME_CONTRACT = """## Runtime Tool And Output Contract

You have FOUR tools.

- `semantic_search_candidates(query, limit)` — Qdrant fuzzy/deconstructed recall. Returns both base candidates and facet descriptors (`termType="f"`). Call once with the verbatim source text. Call again with a single modifier as the query when you need a specific facet descriptor.
- `wiki_ask_guidance(question)` — per-case strategic guidance. Ask which facet families apply to each modifier and which business rules constrain your construction. Call once per case, naming the source text, the top candidate codes, and every modifier you listed.
- `catalog_get_term(code)` — lookup by known code. Returns name, term type, scope note, hierarchies, implicit facets, monitoring flags. Not a search; do not call with a free-text query.
- `validator_validate_code(code, domain, context)` — validate a constructed code. Clean validation is the finalize gate. Hard warnings drive one targeted repair; soft warnings are advisory.

Discipline:

- Use only the provided tools. Do not use FoodEx2 facts from memory.
- Every tool call requires a `tool_rationale` audit object stating the source fact, expected answer, whether it can change the code, and the fallback if no useful result.
- One concept per recall query. Do not combine multiple modifiers in a single `semantic_search_candidates` query when searching for facet descriptors.
- Return final JSON only after the validator has been called on the full constructed code (not just a bare base) and accepted it, or has produced a hard warning you have already addressed once.
- BEFORE finalizing: every modifier from the source text must have a disposition in `factCoverage` — covered by the base (`implicit_in_base`), attached as an `explicit_facet`, or recorded as `not_codeable` only after recall surfaced no descriptor.
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
