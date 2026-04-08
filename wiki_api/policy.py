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
    r"^- `(?P<id>[^`]+)`: (?P<pattern>.+?)(?: Reject\.)?$",
    re.MULTILINE,
)


def _section_map(body: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(body))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[match.group("title").strip()] = body[start:end].strip()
    return sections


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

    constitution = [
        {
            "id": match.group("id"),
            "text": match.group("text").strip(),
            "priority": int(match.group("priority")),
        }
        for match in CONSTITUTION_RE.finditer(sections.get("Constitution", ""))
    ]
    decision_procedure = [
        {
            "step": int(match.group("step")),
            "name": match.group("name"),
            "instruction": match.group("instruction").strip(),
        }
        for match in DECISION_STEP_RE.finditer(sections.get("Decision Procedure", ""))
    ]
    binding_rules: list[dict[str, Any]] = []
    for match in BINDING_RULE_RE.finditer(sections.get("Binding Rules", "")):
        rule: dict[str, Any] = {
            "id": match.group("id"),
            "when": match.group("when"),
        }
        kind = match.group("kind")
        if kind == "must":
            rule["must"] = match.group("text").strip()
        elif kind == "must not":
            rule["must_not"] = match.group("text").strip()
        elif kind == "may":
            rule["may"] = match.group("text").strip()
        binding_rules.append(rule)

    tie_break_rules = [
        {
            "id": match.group("id"),
            "when": match.group("when"),
            "prefer": match.group("prefer").strip(),
        }
        for match in TIE_BREAK_RE.finditer(sections.get("Tie-Break Rules", ""))
    ]
    anti_patterns = [
        {
            "id": match.group("id"),
            "pattern": match.group("pattern").strip(),
            "reject": True,
        }
        for match in ANTI_PATTERN_RE.finditer(sections.get("Anti-Patterns", ""))
    ]

    return {
        "policy_version": version_match.group("version"),
        "constitution": constitution,
        "decision_procedure": decision_procedure,
        "binding_rules": binding_rules,
        "tie_break_rules": tie_break_rules,
        "anti_patterns": anti_patterns,
    }
