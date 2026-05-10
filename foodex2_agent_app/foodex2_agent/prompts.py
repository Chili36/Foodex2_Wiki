from __future__ import annotations

from pathlib import Path

from .settings import APP_DIR


AGENT_MD_PATH = APP_DIR / "AGENT.md"


RUNTIME_CONTRACT = """## Runtime Tool And Output Contract

- Use only the provided tools. Do not use FoodEx2 facts from memory.
- First call `plan_foodex2_coding_strategy`, then call `wiki_ask_guidance` with a broad "what should I think about?" version of the task. Ask the wiki to keep the answer very to the point.
- Do not search for building blocks until you have both a food-type/base-code hypothesis and wiki guidance.
- Treat `wiki_ask_guidance` as the FoodEx2 guide. Use `wiki_policy_pack`, `wiki_context`, or `wiki_read_page` only when additional page-level guidance is needed.
- Use `semantic_search_candidates` for recall only; verify plausible semantic candidates with `catalog_get_term` before selecting them.
- Use catalogue/database tools for term types, scope notes, hierarchy, facet families, and implicit facets.
- Use `validator_validate_code` on every constructed code before the final answer.
- Return final JSON only when you have called the validator at least once.
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
