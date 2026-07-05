---
title: "FoodEx2 In Contaminants Monitoring"
select_when: >-
  The case is reported under contaminants or occurrence monitoring and needs
  the substance-specific reporting details for that domain: cooking-extent,
  packaging-material, fat-content, or target-consumer facets, and preparation
  assumptions that differ from the pesticide reading of the same matrix.
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "Reportable Scallops list of FoodEx2 codes - MTX.xlsx"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[pesticides-foodex2]]"
  - "[[domoic-acid-scallops]]"
  - "[[domain-specific-validation]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-05-19"
---

# FoodEx2 In Contaminants Monitoring

<!-- Source: ChemMon 2026 FoodEx2 mapping section; ChemMon 2026 Table 8 introduction; ChemMon 2026 CHEMMON12; ChemMon 2026 copper sample preparation examples -->
## Use Only When Contaminants Context Is Active

- This page is a conditional domain overlay. Use it when the request, reporting context, legal reference, parameter hierarchy, or candidate collection indicates contaminants monitoring.
- Typical activation signals include contaminants, occurrence, `OCC`, `chemAnalysis`, pyrrolizidine alkaloids, acrylamide, domoic acid, furans, bisphenols, phthalates, heavy metals, or a contaminants-domain candidate set.
- Do not apply pesticide MATRIX constraints to contaminants cases unless the request explicitly says the result is also being reported in the pesticide domain.

## Domain Boundary

- Contaminants coding still starts with ordinary FoodEx2 base-term selection from the MTX reporting hierarchy.
- Contaminants workflows can add substance-specific mandatory or recommended details. These requirements are updated in ChemMon guidance and should be treated as reporting overlays, not as universal FoodEx2 syntax.
- If a contaminant case names a botanical species or variety that is not available as a returned FoodEx2 candidate, use the best valid FoodEx2 candidate for the contaminants context and preserve the extra detail outside the code where the reporting workflow allows free text.

## High-Impact Rules

- Acrylamide monitoring is the clearest exception to normal implicit-facet cleanup: CHEMMON12 requires explicit `F33 Legislative-classes` for acrylamide results, even when the base term already has the relevant legislative class implicitly.
- Domoic acid in scallops has a source-provided matrix lookup. Use [[domoic-acid-scallops]] to select the exact `sampMatCode` and `sampMatText`, and include `origFishAreaCode` from FAREA wherever possible.
- Heat-treatment reporting for furans or acrylamide can require or recommend `F17 Cooking extent`.
- Bisphenol or phthalate analysis can require or recommend `F19 Packaging-material`.
- Fat-weight expression can require or recommend `F07 Fat-content`.
- Infant or baby-food reporting can require or recommend `F23 Target-consumer` when the base term does not already make the target consumer clear.

## Pesticide Contrast

- Some contaminant and pesticide cases use different sample-preparation facets for the same matrix. For copper, contaminants examples include without peel, without shell, without stone, kernels without cob, roasted coffee beans, muscle with fat, and washed plant products.
- These contrasts are domain-specific. If the domain is contaminants, do not borrow pesticide preparation assumptions merely because the substance also appears in pesticide legislation.

## Worked Signals

- Acrylamide on french fries should include the explicit acrylamide legislative class facet, such as `A0BYV#F33.A169H`, when the acrylamide reporting rule is active.
- Domoic acid in scallops should use the species-and-part row from [[domoic-acid-scallops]] instead of a generic scallop code when the source sample identifies the analysed matrix.
- Copper in citrus fruit under contaminants should follow the contaminants preparation assumption, not the pesticide-residue with-peel assumption.
- Pyrrolizidine alkaloids in herbal infusion material should use the contaminants-context candidate set. Do not force the term into a pesticide Annex I MATRIX result unless pesticide reporting is explicit.

## Relevant Policy

- [[domain-specific-validation]] lists the contextual validation checks that turn these recommendations into blocking or warning behavior.
- [[pesticides-foodex2]] is separate because legal MATRIX mapping and sample-preparation assumptions can differ.
- [[implicit-vs-explicit-facets]] still applies unless a contaminants rule explicitly overrides it.
