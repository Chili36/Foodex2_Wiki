from __future__ import annotations

from pathlib import Path
from typing import Any

from .wiki_store import split_frontmatter


REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PAGE_PATH = REPO_ROOT / "raw" / "efsa-guidance" / "policy-contract.md"


def build_policy_contract() -> dict[str, Any]:
    """Load the policy contract from the markdown source page.

    The service should expose policy, not own it. The source of truth therefore
    lives in the repo's markdown layer, and this loader simply extracts the
    structured frontmatter fields needed by the API.
    """

    raw = POLICY_PAGE_PATH.read_text(encoding="utf-8")
    frontmatter, _body = split_frontmatter(raw)

    return {
        "policy_version": frontmatter["policy_version"],
        "constitution": frontmatter.get("constitution", []),
        "decision_procedure": frontmatter.get("decision_procedure", []),
        "binding_rules": frontmatter.get("binding_rules", []),
        "tie_break_rules": frontmatter.get("tie_break_rules", []),
        "anti_patterns": frontmatter.get("anti_patterns", []),
    }
