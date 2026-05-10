---
title: "FoodEx2 In VMPR Monitoring"
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - FoodEx2 maintenance 2024.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[term-type-facet-constraints]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2024]]"
last_updated: "2026-05-09"
---

# FoodEx2 In VMPR Monitoring

<!-- Source: ChemMon 2026 VMPR-specific FoodEx2 sections; ChemMon 2025 VMPR-specific FoodEx2 sections; FoodEx2 maintenance 2024 VetDrugRes updates -->
## Use Only When VMPR Context Is Active

- This page is a conditional domain overlay. Use it when the request, reporting context, legal reference, parameter hierarchy, or candidate collection indicates veterinary medicinal product residue monitoring.
- Typical activation signals include VMPR, VETDRUG, veterinary drug residues, Regulation (EU) No 37/2010, `vmprParam`, `vmprCls`, VetDrugRes, Plan 3, or a VMPR-domain FoodEx2 candidate set.
- Do not apply VMPR explicit-facet requirements to ordinary all-domain FoodEx2 coding unless the domain is active.

## Core VMPR Requirements

- For standard VMPR animal-product matrices, `F01 Source` and `F02 Part-nature` must be present. This is stricter than ordinary FoodEx2 coding because VMPR category mapping can use explicit facets to override implicit categorisation.
- For processed derivatives under VMPR, `F01` may need to be added explicitly because the animal source is not always implicit on processed terms such as dried egg or milk powder.
- Wild animal VMPR samples require `F21.A07RY` (`Wild, gathered or hunted`).
- Non-food animal matrices use `A0C60 Non-food animal-related matrices` with explicit `F01 Source` and `F02 Part-nature`.

## Feed And Water

- VMPR feed and water cases are exceptions to the ordinary animal-product pattern.
- Feed should use terms from the feed section and must contain implicit or explicit `F23 Target-consumer` for the relevant animal category where VMPR mapping needs it.
- Generic `F23.A07TV Animal feed` can classify to `Other`; a species-specific `F23` can map to a specific VMPR category.
- Conflicting target-consumer facets can force classification to `Other`.
- Water intended for farmed animals should use the relevant non-food environmental matrix with `F23 Target-consumer`.

## Processed Products And F33

- VMPR Plan 3 processed products use `F33 Legislative-classes` under the VMPR legislative parent, with only one `F33`.
- The `F33` facet maps the product to the main VMPR legislative commodity. This is a reporting-domain overlay and must still respect FoodEx2 code syntax and single-cardinality rules.
- Maintenance 2024 reorganised VMPR-related reporting around the VetDrugRes hierarchy and added dedicated processed-product legislative classes. Use current VMPR candidate sets rather than old assumptions.

## Worked Signals

- Cow hair in VMPR: `A0C60#F02.A0ESP$F01.A057E`, because non-food animal matrices require explicit part and source.
- Feed for pigs: use a feed base term with pig target-consumer, for example `A0BBB#F23.A07VC` when that base term is the correct feed candidate.
- Wild deer meat in VMPR: add `F21.A07RY` when the wild status is known and not implicit.

## Relevant Policy

- [[term-type-facet-constraints]] still controls facet legality by term type.
- [[implicit-vs-explicit-facets]] explains why VMPR is exceptional: explicit facets can affect classification and are not neutral repetition.
- [[domain-specific-validation]] contains the validation checks that enforce VMPR mandatory facets.

