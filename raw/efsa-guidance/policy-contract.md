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
---

# Policy Contract

This page is the small always-on policy layer for the FoodEx2 wiki service.

It is intentionally separate from the ordinary guidance pages:

- the guidance pages explain FoodEx2
- this page states the decision order that the solver must follow

The API reads this page and exposes its rule sections as the machine-readable `policy_contract`, but the visible markdown body is the canonical source of truth.

## What This Is For

- Make rule priority explicit.
- Prevent the solver from treating all retrieved guidance as a flat bag of considerations.
- Preserve a thin solver prompt by keeping the policy source in the knowledge base rather than in service code.

## Policy Version

`2026-04-08-v0.4`

## Reading Order

Apply this page in the following order:

1. Constitution
2. Decision procedure
3. Binding rules
4. Tie-break rules
5. Anti-patterns

The ordinary wiki pages remain the supporting knowledge layer under this policy.

## Constitution

- `C01` [priority 100]: Determine food type before choosing the base term.
- `C02` [priority 95]: Evaluate specificity only within the chosen food type.
- `C03` [priority 95]: Prefer an existing derivative base over reconstructing the food from a raw commodity plus F28 when FoodEx2 already has the processed group.
- `C04` [priority 90]: Do not restate a process already implicit in the chosen base term.
- `C05` [priority 85]: Examples illustrate rules and never override higher-priority binding rules.
- `C06` [priority 92]: Always use the most detailed reportable non-hierarchy term available as the base term; do not code with hierarchy terms when a reportable entry exists.
- `C07` [priority 92]: Specify origin with the facet family that matches the chosen food type: F27 for derivatives, F04 for composites, and no explicit F01 when the selected base is already a raw primary commodity.
- `C08` [priority 90]: Add only explicit facets that contribute information not already implicit in the chosen base term.
- `C09` [priority 94]: Read the candidate scope note before finalising the base term and reject terms whose scope does not truly cover the product.

## Decision Procedure

1. `determine_food_type`: Classify the food as raw commodity, derivative, composite, or unclear.
2. `read_scope_notes_and_select_candidates_within_type`: Read scope notes, then compare candidates primarily within the selected food type and prefer the most detailed reportable non-hierarchy term within that type.
3. `apply_origin_and_tie_break_rules`: Use derivative-base priority, correct origin-facet family, and anti-pattern rejection before local specificity.
4. `compose_code`: Choose the base term, then add only justified explicit facets.
5. `validate_output`: Check that no explicit facet duplicates an implicit property, no hierarchy base term was used improperly, and no disallowed construction remains.

## Binding Rules

- `R-DERIV-001` when `food_type=derivative and derivative_base_exists=true`: must select the derivative base rather than a raw commodity base.
- `R-IMPLICIT-001` when `chosen_base_already_implies_process=true`: must not add the same process again as explicit F28.
- `R-HIER-001` when `a reportable non-hierarchy candidate exists`: must not select a hierarchy term as the coding base.
- `R-ORIGIN-001` when `food_type=derivative`: must express origin with F27 rather than F04 or F01, unless a separate minor added ingredient rule explicitly applies.
- `R-ORIGIN-002` when `food_type=composite`: must express characterising origin with F04 rather than F27 or F01.
- `R-ORIGIN-003` when `food_type=raw_primary_commodity`: must not add explicit F01 merely to restate the selected raw base commodity.
- `R-FACET-001` when `an explicit facet only repeats an implicit property of the chosen base`: must not keep that explicit facet in the final code.
- `R-SCOPE-001` when `a candidate scope note excludes the described product or narrows it away from the query`: must not select that candidate as the base term.
- `R-DESC-001` when `F10 or F21 information is present and not already implicit in a reportable base term`: may add the descriptive facet explicitly.
- `R-PROC-001` when `multiple explicit F28 processes are added`: must keep at most one process per ordinal group.
- `R-PROC-002` when `the chosen base already implies a process`: must ensure any remaining explicit F28 is at least as specific as the implicit process.
- `R-CARD-001` when `using F03, F11, F17, F20, F22, F23, F24, or F26`: must keep only one value for that facet family.
- `R-F27-001` when `an explicit F27 is used`: must make the F27 refine or equal the implicit or source commodity chain.
- `R-F03-001` when `food_type=raw_primary_commodity`: must not add F03 unless the described processing is only physical division or dimension reduction.
- `R-F01-004` when `food_type=derivative and explicit F01 is present`: must use F01 only when the derivative rules permit it, including the single-F27 dependency.
- `R-SYNTAX-001` when `composing the final code`: must use the syntax base#facetType.code($facetType2.code2...).
- `R-LENGTH-001` when `composing the facet string`: must keep the full facet string at or below 256 characters.
- `R-MONITOR-001` when `returning the final coded result`: must carry the monitoring flags from the base term unchanged.

## Tie-Break Rules

- `TB-001` when `candidate_A is a derivative base and candidate_B is raw+F28 for the same described food`: prefer candidate_A.
- `TB-002` when `a raw candidate is more specific but a derivative candidate better matches the already-selected food type`: prefer the derivative candidate.

## Anti-Patterns

- `AP-001`: raw base + F28 used to recreate a standard derivative group. Reject.

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

## Relevant Policy

- This page is itself the policy layer. Apply it before the ordinary guidance pages whenever a solver or coder needs decision order rather than only background knowledge.
- Read it in the order already defined here: constitution, decision procedure, binding rules, tie-break rules, then anti-patterns.

## Relevant Business Rules

- [[business-rules]] remains a narrower validator layer. It does not replace this page; it checks whether the chosen construction violates `BRxx` constraints after the policy has been applied.
- The most common handoff points are reportability and hierarchy issues (`BR08`, `BR23`, `BR24`), facet/cardinality checks (`BR25`), and structural validity (`BR29-BR31`).
