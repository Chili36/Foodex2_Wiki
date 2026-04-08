---
title: "Policy Contract"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[base-term-selection]]"
  - "[[process-facets]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-04-08"
policy_version: "2026-04-08-v0.3"
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
  - id: "C06"
    text: "Always use the most detailed reportable non-hierarchy term available as the base term; do not code with hierarchy terms when a reportable entry exists."
    priority: 92
  - id: "C07"
    text: "Specify origin with the facet family that matches the chosen food type: F27 for derivatives, F04 for composites, and no explicit F01 when the selected base is already a raw primary commodity."
    priority: 92
  - id: "C08"
    text: "Add only explicit facets that contribute information not already implicit in the chosen base term."
    priority: 90
decision_procedure:
  - step: 1
    name: "determine_food_type"
    instruction: "Classify the food as raw commodity, derivative, composite, or unclear."
  - step: 2
    name: "select_candidates_within_type"
    instruction: "Compare candidates primarily within the selected food type and prefer the most detailed reportable non-hierarchy term within that type."
  - step: 3
    name: "apply_origin_and_tie_break_rules"
    instruction: "Use derivative-base priority, correct origin-facet family, and anti-pattern rejection before local specificity."
  - step: 4
    name: "compose_code"
    instruction: "Choose the base term, then add only justified explicit facets."
  - step: 5
    name: "validate_output"
    instruction: "Check that no explicit facet duplicates an implicit property, no hierarchy base term was used improperly, and no disallowed construction remains."
binding_rules:
  - id: "R-DERIV-001"
    when: "food_type=derivative and derivative_base_exists=true"
    must: "select the derivative base rather than a raw commodity base"
  - id: "R-IMPLICIT-001"
    when: "chosen_base_already_implies_process=true"
    must_not: "add the same process again as explicit F28"
  - id: "R-HIER-001"
    when: "a reportable non-hierarchy candidate exists"
    must_not: "select a hierarchy term as the coding base"
  - id: "R-ORIGIN-001"
    when: "food_type=derivative"
    must: "express origin with F27 rather than F04 or F01, unless a separate minor added ingredient rule explicitly applies"
  - id: "R-ORIGIN-002"
    when: "food_type=composite"
    must: "express characterising origin with F04 rather than F27 or F01"
  - id: "R-ORIGIN-003"
    when: "food_type=raw_primary_commodity"
    must_not: "add explicit F01 merely to restate the selected raw base commodity"
  - id: "R-FACET-001"
    when: "an explicit facet only repeats an implicit property of the chosen base"
    must_not: "keep that explicit facet in the final code"
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

## Ground Rules

These are the practical ground rules the solver should always keep in view:

1. Identify the food type first: raw primary commodity, derivative, or composite.
2. Avoid hierarchy terms as coding bases when a reportable non-hierarchy term exists.
3. Specify origin precisely with the facet family that matches the chosen food type.
4. Add only explicit facets that contribute information not already implicit in the base term.
