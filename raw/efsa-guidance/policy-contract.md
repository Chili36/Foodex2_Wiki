---
title: "Policy Contract"
sources:
  - "EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf"
  - "EFSA Supporting Publications - 2018 - Training on FoodEx2.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[base-term-selection]]"
  - "[[process-facets]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-04-07"
policy_version: "2026-04-07-v0.2"
constitution:
  - id: "C01"
    text: "Determine food type before choosing the base term."
    priority: 100
  - id: "C02"
    text: "Evaluate specificity only within the chosen food type."
    priority: 95
  - id: "C03"
    text: "Prefer an existing derivative base over reconstructing the food from a raw commodity plus F28 when FoodEx2 already has the processed group."
    priority: 95
  - id: "C04"
    text: "Do not restate a process already implicit in the chosen base term."
    priority: 90
  - id: "C05"
    text: "Examples illustrate rules and never override higher-priority binding rules."
    priority: 85
decision_procedure:
  - step: 1
    name: "determine_food_type"
    instruction: "Classify the food as raw commodity, derivative, composite, or unclear."
  - step: 2
    name: "select_candidates_within_type"
    instruction: "Compare candidates primarily within the selected food type."
  - step: 3
    name: "apply_binding_and_tie_break_rules"
    instruction: "Use derivative-base priority and anti-pattern rejection before local specificity."
  - step: 4
    name: "compose_code"
    instruction: "Choose the base term, then add only justified explicit facets."
  - step: 5
    name: "validate_output"
    instruction: "Check that no explicit facet duplicates an implicit property and no disallowed construction remains."
binding_rules:
  - id: "R-DERIV-001"
    when: "food_type=derivative and derivative_base_exists=true"
    must: "select the derivative base rather than a raw commodity base"
  - id: "R-IMPLICIT-001"
    when: "chosen_base_already_implies_process=true"
    must_not: "add the same process again as explicit F28"
tie_break_rules:
  - id: "TB-001"
    when: "candidate_A is a derivative base and candidate_B is raw+F28 for the same described food"
    prefer: "candidate_A"
  - id: "TB-002"
    when: "a raw candidate is more specific but a derivative candidate better matches the already-selected food type"
    prefer: "the derivative candidate"
anti_patterns:
  - id: "AP-001"
    pattern: "raw base + F28 used to recreate a standard derivative group"
    reject: true
---

# Policy Contract

This page is the small always-on policy layer for the FoodEx2 wiki service.

It is intentionally separate from the ordinary guidance pages:

- the guidance pages explain FoodEx2
- this page states the decision order that the solver must follow

The API reads the structured fields in this page's frontmatter and returns them as the machine-readable `policy_contract`.

## What This Is For

- Make rule priority explicit.
- Prevent the solver from treating all retrieved guidance as a flat bag of considerations.
- Preserve a thin solver prompt by keeping the policy source in the knowledge base rather than in service code.

## Reading Order

Apply this page in the following order:

1. Constitution
2. Decision procedure
3. Binding rules
4. Tie-break rules
5. Anti-patterns

The ordinary wiki pages remain the supporting knowledge layer under this policy.
