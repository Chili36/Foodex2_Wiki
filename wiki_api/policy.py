from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .wiki_store import split_frontmatter


REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PAGE_PATH = REPO_ROOT / "raw" / "efsa-guidance" / "policy-contract.md"

SECTION_RE = re.compile(r"^## (?P<title>.+?)\s*$", re.MULTILINE)
VERSION_RE = re.compile(r"^`(?P<version>[^`]+)`$", re.MULTILINE)
CONSTITUTION_RE = re.compile(
    r"^- `(?P<id>[^`]+)` \[priority (?P<priority>\d+)\]: (?P<text>.+)$",
    re.MULTILINE,
)
DECISION_STEP_RE = re.compile(
    r"^(?P<step>\d+)\. `(?P<name>[^`]+)`: (?P<instruction>.+)$",
    re.MULTILINE,
)
BINDING_RULE_RE = re.compile(
    r"^- `(?P<id>[^`]+)` when `(?P<when>[^`]+)`: (?P<kind>must not|must|may) (?P<text>.+)$",
    re.MULTILINE,
)
TIE_BREAK_RE = re.compile(
    r"^- `(?P<id>[^`]+)` when `(?P<when>[^`]+)`: prefer (?P<prefer>.+)$",
    re.MULTILINE,
)
ANTI_PATTERN_RE = re.compile(
    r"^- `(?P<id>[^`]+)`: (?P<pattern>.+)$",
    re.MULTILINE,
)
DERIVED_FROM_RE = re.compile(r"\s+\{derived_from:\s*(?P<items>[^}]+)\}\s*$")


def _section_map(body: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(body))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[match.group("title").strip()] = body[start:end].strip()
    return sections


def _split_derived_from(text: str) -> tuple[str, list[str]]:
    cleaned = text.strip()
    match = DERIVED_FROM_RE.search(cleaned)
    if match is None:
        return cleaned, []
    derived_from = [item.strip() for item in match.group("items").split(";") if item.strip()]
    return cleaned[: match.start()].rstrip(), derived_from


def build_policy_contract() -> dict[str, Any]:
    """Load the policy contract from the markdown source page.

    The service should expose policy, not own it. The source of truth therefore
    lives in the repo's markdown layer, and this loader parses the canonical
    markdown body into the structured fields needed by the API.
    """

    raw = POLICY_PAGE_PATH.read_text(encoding="utf-8")
    _frontmatter, body = split_frontmatter(raw)
    sections = _section_map(body)

    version_match = VERSION_RE.search(sections.get("Policy Version", ""))
    if version_match is None:
        raise ValueError("policy-contract.md is missing a parseable 'Policy Version' section")

    constitution = []
    for match in CONSTITUTION_RE.finditer(sections.get("Constitution", "")):
        text, derived_from = _split_derived_from(match.group("text"))
        constitution.append(
            {
                "id": match.group("id"),
                "text": text,
                "priority": int(match.group("priority")),
                "derived_from": derived_from,
            }
        )

    decision_procedure = []
    for match in DECISION_STEP_RE.finditer(sections.get("Decision Procedure", "")):
        instruction, derived_from = _split_derived_from(match.group("instruction"))
        decision_procedure.append(
            {
                "step": int(match.group("step")),
                "name": match.group("name"),
                "instruction": instruction,
                "derived_from": derived_from,
            }
        )
    binding_rules: list[dict[str, Any]] = []
    for match in BINDING_RULE_RE.finditer(sections.get("Binding Rules", "")):
        text, derived_from = _split_derived_from(match.group("text"))
        rule: dict[str, Any] = {
            "id": match.group("id"),
            "when": match.group("when"),
            "derived_from": derived_from,
        }
        kind = match.group("kind")
        if kind == "must":
            rule["must"] = text
        elif kind == "must not":
            rule["must_not"] = text
        elif kind == "may":
            rule["may"] = text
        binding_rules.append(rule)

    tie_break_rules = []
    for match in TIE_BREAK_RE.finditer(sections.get("Tie-Break Rules", "")):
        prefer, derived_from = _split_derived_from(match.group("prefer"))
        tie_break_rules.append(
            {
                "id": match.group("id"),
                "when": match.group("when"),
                "prefer": prefer,
                "derived_from": derived_from,
            }
        )

    anti_patterns = []
    for match in ANTI_PATTERN_RE.finditer(sections.get("Anti-Patterns", "")):
        pattern, derived_from = _split_derived_from(match.group("pattern"))
        if pattern.endswith(" Reject."):
            pattern = pattern[: -len(" Reject.")].rstrip()
        anti_patterns.append(
            {
                "id": match.group("id"),
                "pattern": pattern,
                "reject": True,
                "derived_from": derived_from,
            }
        )

    return {
        "policy_version": version_match.group("version"),
        "constitution": constitution,
        "decision_procedure": decision_procedure,
        "binding_rules": binding_rules,
        "tie_break_rules": tie_break_rules,
        "anti_patterns": anti_patterns,
    }
