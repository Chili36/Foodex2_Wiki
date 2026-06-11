---
title: "FoodEx2 In VMPR Monitoring"
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - FoodEx2 maintenance 2024.pdf"
  - "EFSA Supporting Publications - 2022 -  - FoodEx2 maintenance 2021.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[term-type-facet-constraints]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2024]]"
last_updated: "2026-06-10"
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

## Non-Food Biological Sample Boundary

- In active VMPR reporting, if the sampled matrix is a non-food biological sample, use `A0C60 Non-food animal-related matrices` with explicit `F01 Source` and `F02 Part-nature`, even when a more food-like animal-product term exists. ChemMon gives urine, retina, hair, and blood serum as non-food VMPR examples using this pattern. (ChemMon 2025 p36; ChemMon 2026 p36)
- Whole blood is a structural grey area. The FoodEx2 catalogue also contains food-chain blood terms, while maintenance 2021 added blood-related `F02` descriptors for ASF/WGS biological sample description. In active VMPR biological-sample rows, use the non-food biological-sample convention: code blood, blood serum, and plasma as `A0C60` plus the catalogue-confirmed `F02` part-nature and explicit `F01` animal source, unless the source text explicitly says the row is an edible blood product, blood ingredient, slaughterhouse food-chain commodity, or ordinary all-domain food matrix outside VMPR. (FoodEx2 maintenance 2021 p2, p10; ChemMon 2025 p36; ChemMon 2026 p36)
- `A0C60` is an intentional VMPR non-food exception to the ordinary preference for the most specific food base term. The specificity comes from the explicit facets: `F01` identifies the animal source and `F02` identifies the biological matrix.
- The ChemMon examples do not enumerate every species/blood wording. Treat bare `blood`, `serum`, or `plasma` in an active VMPR biological-sample row as non-food sampling language, not as evidence for an edible-blood food base term. Use the normal FoodEx2 base-term workflow when food-chain use is explicit, when a source flag such as `is_food=true` identifies the row as food, or when VMPR biological-sample context is absent.

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
- Sheep blood serum in VMPR: `A0C60#F01.A0CDE$F02.A0CEY`, because ChemMon treats blood serum as a non-food animal-related matrix with explicit animal source and part-nature.
- Blood, serum, or plasma biological sample in VMPR: keep `A0C60` as the base; attach `F02.A06AL` for blood, `F02.A0CEY` for blood serum, or `F02.A0CEX` for plasma, plus the catalogue-confirmed `F01` source animal.
- For VMPR non-food biological sample rows, keep `A0C60` as the base and attach the catalogue-confirmed `F02` descriptor for the sampled matrix plus the relevant explicit `F01` animal source.
- Feed for pigs: use a feed base term with pig target-consumer, for example `A0BBB#F23.A07VC` when that base term is the correct feed candidate.
- Wild deer meat in VMPR: add `F21.A07RY` when the wild status is known and not implicit.

## Relevant Policy

- [[term-type-facet-constraints]] still controls facet legality by term type.
- [[implicit-vs-explicit-facets]] explains why VMPR is exceptional: explicit facets can affect classification and are not neutral repetition.
- [[domain-specific-validation]] contains the validation checks that enforce VMPR mandatory facets.
