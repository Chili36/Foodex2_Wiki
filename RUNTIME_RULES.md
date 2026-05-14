---
title: "Runtime Rules"
last_updated: "2026-05-09"
sources:
  - "raw/efsa-guidance/policy-contract.md"
  - "raw/efsa-guidance/base-term-selection.md"
  - "raw/efsa-guidance/term-type-facet-constraints.md"
  - "raw/efsa-guidance/implicit-vs-explicit-facets.md"
  - "raw/efsa-guidance/business-rules.md"
related:
  - "[[policy-contract]]"
  - "[[base-term-selection]]"
  - "[[term-type-facet-constraints]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[business-rules]]"
---

# Runtime Rules

This is the compact prompt-facing rules file for `context-pack`.

Use it as the always-on runtime layer before the supporting guidance pages.

## Core Decision Order

1. Determine food type first: raw commodity, derivative, or composite.
2. Choose the best reportable non-hierarchy base term within that food type.
3. If FoodEx2 already has a derivative or composite base that captures the processed state, use it instead of reconstructing the food from a raw base plus explicit facets.
4. Add only explicit facets that contribute information not already implicit in the chosen base term.
5. Validate the construction against facet legality, process rules, hierarchy/reportability limits, and code syntax.

## Always-On Rules

- Prefer a reportable non-hierarchy base term over a hierarchy, group, or facet term.
- Evaluate specificity within the selected food type, not across raw-vs-derivative candidates.
- For derivatives, origin normally uses `F27`.
- For composites, characterising ingredients normally use `F04`.
- Do not use explicit `F01` merely to restate a raw base commodity.
- Do not duplicate implicit facets explicitly.
- Do not reconstruct a standard derivative group from a raw base plus `F28` when the derivative group already exists.
- Treat reporting-domain overlays as opt-in; do not infer a domain unless context or domain-filtered candidates identify it.
- If the needed code is not present in the candidate list, do not invent it.

## Supporting Pages By Signal

- Base-term choice or mixed term types: `base-term-selection.md`
- Raw-vs-derivative or facet legality questions: `term-type-facet-constraints.md`
- Implicit vs explicit detail: `implicit-vs-explicit-facets.md`
- Processing: `process-facets.md` and `process-validation-rules.md`
- Ingredients or composites: `ingredient-facets.md`
- Packaging: `packaging-facets.md`
- Reporting-domain overlays are conditional. Use them only when the domain is explicit or the candidate set is domain-filtered: `pesticides-foodex2.md`, `contaminants-foodex2.md`, `vmpr-foodex2.md`, `additives-flavourings-foodex2.md`, and `domain-specific-validation.md`

## Authority

- `policy-contract.md` is the richer execution-order page.
- `business-rules.md` is the canonical validator-rule page for `BRxx` constraints.
- Supporting guidance pages explain how to apply those authorities to a coding case.
