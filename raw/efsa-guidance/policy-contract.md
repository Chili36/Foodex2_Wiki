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
policy_version: "2026-04-08-v0.4"
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
  - id: "C09"
    text: "Read the candidate scope note before finalising the base term and reject terms whose scope does not truly cover the product."
    priority: 94
decision_procedure:
  - step: 1
    name: "determine_food_type"
    instruction: "Classify the food as raw commodity, derivative, composite, or unclear."
  - step: 2
    name: "read_scope_notes_and_select_candidates_within_type"
    instruction: "Read scope notes, then compare candidates primarily within the selected food type and prefer the most detailed reportable non-hierarchy term within that type."
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
  - id: "R-SCOPE-001"
    when: "a candidate scope note excludes the described product or narrows it away from the query"
    must_not: "select that candidate as the base term"
  - id: "R-DESC-001"
    when: "F10 or F21 information is present and not already implicit in a reportable base term"
    may: "add the descriptive facet explicitly"
  - id: "R-PROC-001"
    when: "multiple explicit F28 processes are added"
    must: "keep at most one process per ordinal group"
  - id: "R-PROC-002"
    when: "the chosen base already implies a process"
    must: "ensure any remaining explicit F28 is at least as specific as the implicit process"
  - id: "R-CARD-001"
    when: "using F03, F11, F17, F20, F22, F23, F24, or F26"
    must: "keep only one value for that facet family"
  - id: "R-F27-001"
    when: "an explicit F27 is used"
    must: "make the F27 refine or equal the implicit or source commodity chain"
  - id: "R-F03-001"
    when: "food_type=raw_primary_commodity"
    must_not: "add F03 unless the described processing is only physical division or dimension reduction"
  - id: "R-F01-004"
    when: "food_type=derivative and explicit F01 is present"
    must: "use F01 only when the derivative rules permit it, including the single-F27 dependency"
  - id: "R-SYNTAX-001"
    when: "composing the final code"
    must: "use the syntax base#facetType.code($facetType2.code2...)"
  - id: "R-LENGTH-001"
    when: "composing the facet string"
    must: "keep the full facet string at or below 256 characters"
  - id: "R-MONITOR-001"
    when: "returning the final coded result"
    must: "carry the monitoring flags from the base term unchanged"
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

## Operational Rules

- Read the scope note first and verify that the candidate truly covers the product before selecting it as the base term.
- Select the most specific existing reportable code within the chosen food type. Use groups only when explicitly asked or when no reportable non-hierarchy term exists.
- Processed term priority is binding: if a derivative or composite term already captures the processed state, use that term instead of reconstructing the product from a raw commodity plus `F28`.
- Apply term-type-specific facet focus:
  - `r`: focus on the most specific raw base term and only simple allowed treatments.
  - `d`: focus on constitutive source with `F27` and on new treatments not already implicit.
  - `c` / `s`: focus on characterising recipe ingredients with `F04` and relevant treatments.
  - `h` / `g`: do not use as coding base terms when a reportable term exists.
- `F10 qualitative-info` and `F21 production-method` are descriptive facets and may be used on reportable base terms when the information is present and not already implicit.
- Implicit facets are already present. Never duplicate them explicitly.
- For `F28`, keep one process per ordinal group and do not add a process that is broader than the one already implicit in the base term.
- Single-cardinality facet families allow only one value: `F03`, `F11`, `F17`, `F20`, `F22`, `F23`, `F24`, and `F26`.
- `F27` must refine or equal the implicit/source commodity chain.
- Do not use `F03` on raw commodities except when the only described processing is physical division or dimension reduction.
- Do not use `F01` on raw commodities. On derivatives, use `F01` only when the derivative rules permit it.
- Code syntax is `base#facetType.code($facetType2.code2...)`.
- The full facet string must stay within the SSD2 limit of 256 characters.
- Carry monitoring flags from the base term unchanged.
