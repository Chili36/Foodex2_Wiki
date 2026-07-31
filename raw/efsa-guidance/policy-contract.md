---
title: "Policy Contract"
select_when: >-
  The case needs an explicit decision order and priority ranking when rules
  pull in different directions: which constraint wins, how to sequence
  food-type, base-term, origin, and validation steps, and which anti-patterns
  to reject before composing the final code.
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[base-term-selection]]"
  - "[[process-facets]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-07-28"
---

# Policy Contract

This page does not create a second body of FoodEx2 law.

Use it as the solver-facing execution order for authorities that live elsewhere:

- [[business-rules]] for validator constraints and `BRxx` authority
- the ordinary guidance pages for FoodEx2 interpretation and coding practice

Apply this page before the other wiki pages when a model needs decision order rather than background explanation.

Every `Cxx`, `R-xxx`, `TB-xxx`, and `AP-xxx` item below includes a `{derived_from: ...}` tag.
If this page and a cited `BRxx` rule or guidance page ever disagree, the cited source wins and this page must be corrected.

## Reading Order

Apply this page in the following order:

1. Constitution
2. Decision procedure
3. Binding rules
4. Tie-break rules
5. Anti-patterns

Use the cited business rules and guidance pages as the controlling sources under this execution order.

## Policy Version

`2026-07-28-v0.7`

## Constitution

- `C01` [priority 100]: Determine food type before choosing the base term. {derived_from: foodex2-overview.md; base-term-selection.md; term-type-facet-constraints.md}
- `C02` [priority 95]: Evaluate specificity only within the chosen food type. {derived_from: base-term-selection.md; term-type-facet-constraints.md}
- `C03` [priority 95]: Prefer an existing derivative base over reconstructing the food from a raw commodity plus `F28` when FoodEx2 already has the processed group. {derived_from: base-term-selection.md; process-facets.md; business-rules.md BR19}
- `C04` [priority 90]: Do not restate a process already implicit in the chosen base term. {derived_from: implicit-vs-explicit-facets.md; process-facets.md; business-rules.md BR16}
- `C05` [priority 85]: Examples illustrate rules and never override higher-priority binding rules. {derived_from: execution-layer}
- `C06` [priority 92]: Always use the most detailed reportable non-hierarchy term available as the base term; do not code with hierarchy terms when a reportable entry exists. {derived_from: base-term-selection.md; business-rules.md BR08; business-rules.md BR23; business-rules.md BR24}
- `C07` [priority 92]: Specify origin with the facet family that matches the chosen food type: raw commodities normally carry `F01` implicitly and may use explicit `F01` to narrow a generic source; derivatives use `F27` for constitutive source; composites use `F04` for characterising ingredients. `F04` may also describe only minor later-added ingredients on raw or derivative terms under `BR12`. {derived_from: term-type-facet-constraints.md; implicit-vs-explicit-facets.md; ingredient-facets.md; business-rules.md BR03; business-rules.md BR04; business-rules.md BR05; business-rules.md BR06; business-rules.md BR07; business-rules.md BR12}
- `C08` [priority 90]: Add only explicit facets that contribute information not already implicit in the chosen base term. {derived_from: implicit-vs-explicit-facets.md; facet-coding-rules.md}
- `C09` [priority 94]: Read the candidate wording and any available coverage text before finalising the base term and reject terms that do not truly cover the product. {derived_from: base-term-selection.md}

## Decision Procedure

1. `determine_food_type`: Classify the food as raw commodity, derivative, composite, or unclear. {derived_from: foodex2-overview.md; base-term-selection.md; term-type-facet-constraints.md}
2. `read_candidate_wording_and_select_candidates_within_type`: Read candidate names and any available coverage text, then compare candidates primarily within the selected food type and prefer the most detailed reportable non-hierarchy term within that type. {derived_from: base-term-selection.md}
3. `apply_origin_and_tie_break_rules`: Use origin-facet family, processed-term priority, and anti-pattern rejection before local specificity. {derived_from: implicit-vs-explicit-facets.md; ingredient-facets.md; process-facets.md; business-rules.md BR19}
4. `compose_code`: Choose the base term, then add only justified explicit facets. {derived_from: facet-coding-rules.md; code-string-format.md; implicit-vs-explicit-facets.md}
5. `validate_output`: Check syntax, hierarchy/reportability, facet compatibility, and process/cardinality conflicts before accepting the final code. {derived_from: validation-rules.md; structural-validation.md; business-rules.md}

## Binding Rules

- `R-DERIV-001` when `food_type=derivative and derivative_base_exists=true`: must select the derivative base rather than reconstructing the food from a raw commodity base plus `F28`. {derived_from: base-term-selection.md; process-facets.md; business-rules.md BR19}
- `R-IMPLICIT-001` when `chosen_base_already_implies_process=true`: must not add the same process again as explicit `F28`. {derived_from: implicit-vs-explicit-facets.md; process-facets.md; business-rules.md BR16}
- `R-HIER-001` when `a reportable non-hierarchy candidate exists`: must not select a hierarchy term as the coding base. {derived_from: base-term-selection.md; business-rules.md BR08; business-rules.md BR23; business-rules.md BR24}
- `R-ORIGIN-001` when `food_type=derivative`: must express origin with `F27` rather than `F04` or `F01`, unless a separate minor added ingredient rule explicitly applies. {derived_from: term-type-facet-constraints.md; implicit-vs-explicit-facets.md; ingredient-facets.md; business-rules.md BR05; business-rules.md BR06; business-rules.md BR07}
- `R-ORIGIN-002` when `food_type=composite`: must express characterising origin with `F04` rather than `F27` or `F01`. {derived_from: ingredient-facets.md; term-type-facet-constraints.md; business-rules.md BR03; business-rules.md BR04}
- `R-ORIGIN-003` when `food_type=raw_primary_commodity`: must not add explicit `F01` merely to restate the selected raw base commodity. {derived_from: implicit-vs-explicit-facets.md; term-type-facet-constraints.md}
- `R-ORIGIN-004` when `food_type=raw_primary_commodity and the selected raw base has a generic implicit source and a narrower source is known`: may add explicit `F01` as a restriction to the more detailed source. {derived_from: implicit-vs-explicit-facets.md; base-term-selection.md; term-type-facet-constraints.md}
- `R-INGREDIENT-001` when `food_type=raw_primary_commodity or food_type=derivative and explicit F04 is present`: must use `F04` only for a minor later-added ingredient, coating, flavouring, or decoration; it must not encode the constitutive source. {derived_from: ingredient-facets.md; term-type-facet-constraints.md; business-rules.md BR12}
- `R-FACET-001` when `an explicit facet only repeats an implicit property of the chosen base`: must not keep that explicit facet in the final code. {derived_from: implicit-vs-explicit-facets.md; facet-coding-rules.md}
- `R-SCOPE-001` when `candidate wording or any available coverage text excludes the described product or narrows it away from the query`: must not select that candidate as the base term. {derived_from: base-term-selection.md}
- `R-DESC-001` when `F10 or F21 information is present and not already implicit in a reportable base term`: may add the descriptive facet explicitly. {derived_from: facet-coding-rules.md}
- `R-PROC-001` when `multiple explicit F28 processes are added`: should keep at most one process per ordinal group; note that BR26 may currently be silent in validators, so this is still a construction discipline even when validation does not flag it. {derived_from: process-validation-rules.md; business-rules.md BR26; business-rules.md BR27}
- `R-PROC-002` when `the chosen base already implies a process`: must ensure any remaining explicit `F28` is at least as specific as the implicit process. {derived_from: process-facets.md; process-validation-rules.md; business-rules.md BR16}
- `R-CARD-001` when `using F01, F02, F03, F07, F11, F22, F24, F26, F30, F32, or F34`: must keep only one value for that facet family. {derived_from: business-rules.md BR25; structural-validation.md}
- `R-F27-001` when `an explicit F27 is used`: must make the `F27` refine or equal the implicit or source commodity chain. {derived_from: term-type-facet-constraints.md; business-rules.md BR01; business-rules.md BR05}
- `R-F03-001` when `food_type=raw_primary_commodity and F03 descriptor is in the BR13 disintegration list`: must not add that `F03` to the final code; choose the appropriate derivative base instead. This is not a blanket ban on all `F03` descriptors for raw commodities. {derived_from: term-type-facet-constraints.md; business-rules.md BR13}
- `R-F01-004` when `food_type=derivative and explicit F01 is present`: must use `F01` only when the derivative rules permit it, including the single-`F27` dependency. {derived_from: term-type-facet-constraints.md; business-rules.md BR06; business-rules.md BR07}
- `R-SYNTAX-001` when `composing the final code`: must use the syntax `base#facetType.code($facetType2.code2...)`. {derived_from: code-string-format.md; business-rules.md BR29}
- `R-LENGTH-001` when `composing the facet string`: must keep the full facet string at or below 256 characters. {derived_from: code-string-format.md}

## Tie-Break Rules

- `TB-001` when `candidate_A is a derivative base and candidate_B is raw+F28 for the same described food`: prefer `candidate_A`. {derived_from: base-term-selection.md; process-facets.md; business-rules.md BR19}
- `TB-002` when `a raw candidate is more specific but a derivative candidate better matches the already-selected food type`: prefer the derivative candidate. {derived_from: base-term-selection.md; term-type-facet-constraints.md}

## Anti-Patterns

- `AP-001`: raw base + `F28` used to recreate a standard derivative group. Reject. {derived_from: base-term-selection.md; process-facets.md; business-rules.md BR19}

## Ground Rules

These are the practical ground rules the solver should always keep in view:

1. Identify the food type first: raw primary commodity, derivative, or composite.
2. Avoid hierarchy terms as coding bases when a reportable non-hierarchy term exists.
3. Specify origin precisely with the facet family that matches the chosen food type.
4. Add only explicit facets that contribute information not already implicit in the base term.

## Operational Rules

- Read the candidate wording first and use any available coverage text to verify that the candidate truly covers the product before selecting it as the base term.
- Select the most specific existing reportable code within the chosen food type. Use groups only when explicitly asked or when no reportable non-hierarchy term exists.
- Processed term priority is binding: if a derivative or composite term already captures the processed state, use that term instead of reconstructing the product from a raw commodity plus `F28`.
- Apply term-type-specific facet focus:
  - `r`: focus on the most specific raw base term; use explicit `F01` only to narrow a generic implicit source, and `F04` only for minor later-added ingredients.
  - `d`: focus on constitutive source with `F27`, minor later-added ingredients with `F04`, and new treatments not already implicit.
  - `c` / `s`: focus on characterising recipe ingredients with `F04` and relevant treatments.
  - `h` / `g`: do not use as coding base terms when a reportable term exists.
- `F10 qualitative-info` and `F21 production-method` are descriptive facets and may be used on reportable base terms when the information is present and not already implicit.
- Implicit facets are already present. Never duplicate them explicitly.
- For `F28`, keep one process per ordinal group and do not add a process that is broader than the one already implicit in the base term. BR26 may currently be silent in validators, so do not use validator silence alone as approval for same-ordinal process stacking.
- Single-cardinality facet families allow only one value: `F01`, `F02`, `F03`, `F07`, `F11`, `F22`, `F24`, `F26`, `F30`, `F32`, and `F34`.
- `F27` must refine or equal the implicit/source commodity chain.
- On raw commodities, do not use the BR13 disintegration-family `F03` descriptors: `A06JD`, `A06JE`, `A06JF`, `A06JG`, `A07Y2`, `A07Y3`, or `A07Y4`. Non-disintegration physical-state descriptors are not blocked by BR13 merely because they are `F03`.
- On raw commodities, use explicit `F01` only to narrow a generic implicit source; do not use it merely to restate the selected raw commodity. On derivatives, use `F01` only when the derivative rules permit it.
- On raw or derivative terms, use `F04` only for minor later-added ingredients such as coatings, flavourings, or decorations; do not use it for the constitutive source.
- Code syntax is `base#facetType.code($facetType2.code2...)`.
- The full facet string must stay within the SSD2 limit of 256 characters.

## Relevant Policy

- This page is the execution-order layer. Apply it before the ordinary guidance pages whenever a solver or coder needs decision order rather than only background knowledge.
- Read it in the order already defined here: constitution, decision procedure, binding rules, tie-break rules, then anti-patterns.

## Relevant Business Rules

- [[business-rules]] is a source authority for many items on this page, not merely a post-hoc validator reference.
- When a cited `BRxx` already blocks a construction, treat that `BRxx` rule as the controlling authority; this page only makes the solver apply it earlier and more consistently.
- The most common handoff points are reportability and hierarchy issues (`BR08`, `BR23`, `BR24`), facet/cardinality checks (`BR25`), and structural validity (`BR29-BR31`).
