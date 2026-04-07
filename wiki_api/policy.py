from __future__ import annotations

from typing import Any


POLICY_VERSION = "2026-04-07-v0.2"


def build_policy_contract() -> dict[str, Any]:
    """Return the small always-on policy contract used by the solver.

    This is the minimal policy layer above the wiki: invariant rules, a fixed
    decision order, a few binding rules, and one recurring anti-pattern.
    """

    return {
        "policy_version": POLICY_VERSION,
        "constitution": [
            {
                "id": "C01",
                "text": "Determine food type before choosing the base term.",
                "priority": 100,
            },
            {
                "id": "C02",
                "text": "Evaluate specificity only within the chosen food type.",
                "priority": 95,
            },
            {
                "id": "C03",
                "text": (
                    "Prefer an existing derivative base over reconstructing the food from a "
                    "raw commodity plus F28 when FoodEx2 already has the processed group."
                ),
                "priority": 95,
            },
            {
                "id": "C04",
                "text": "Do not restate a process already implicit in the chosen base term.",
                "priority": 90,
            },
            {
                "id": "C05",
                "text": "Examples illustrate rules and never override higher-priority binding rules.",
                "priority": 85,
            },
        ],
        "decision_procedure": [
            {
                "step": 1,
                "name": "determine_food_type",
                "instruction": "Classify the food as raw commodity, derivative, composite, or unclear.",
            },
            {
                "step": 2,
                "name": "select_candidates_within_type",
                "instruction": "Compare candidates primarily within the selected food type.",
            },
            {
                "step": 3,
                "name": "apply_binding_and_tie_break_rules",
                "instruction": "Use derivative-base priority and anti-pattern rejection before local specificity.",
            },
            {
                "step": 4,
                "name": "compose_code",
                "instruction": "Choose the base term, then add only justified explicit facets.",
            },
            {
                "step": 5,
                "name": "validate_output",
                "instruction": "Check that no explicit facet duplicates an implicit property and no disallowed construction remains.",
            },
        ],
        "binding_rules": [
            {
                "id": "R-DERIV-001",
                "when": "food_type=derivative and derivative_base_exists=true",
                "must": "select the derivative base rather than a raw commodity base",
            },
            {
                "id": "R-IMPLICIT-001",
                "when": "chosen_base_already_implies_process=true",
                "must_not": "add the same process again as explicit F28",
            },
        ],
        "tie_break_rules": [
            {
                "id": "TB-001",
                "when": "candidate_A is a derivative base and candidate_B is raw+F28 for the same described food",
                "prefer": "candidate_A",
            },
            {
                "id": "TB-002",
                "when": "a raw candidate is more specific but a derivative candidate better matches the already-selected food type",
                "prefer": "the derivative candidate",
            },
        ],
        "anti_patterns": [
            {
                "id": "AP-001",
                "pattern": "raw base + F28 used to recreate a standard derivative group",
                "reject": True,
            }
        ],
    }
