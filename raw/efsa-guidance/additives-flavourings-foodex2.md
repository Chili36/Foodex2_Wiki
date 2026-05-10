---
title: "FoodEx2 In Additives And Flavourings Monitoring"
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - FoodEx2 maintenance 2024.pdf"
  - "EFSA Supporting Publications - 2024 -  - FoodEx2 maintenance 2023.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2023]]"
  - "[[maintenance-2024]]"
last_updated: "2026-05-09"
---

# FoodEx2 In Additives And Flavourings Monitoring

<!-- Source: ChemMon 2026 food additives and flavourings section; ChemMon 2026 CHEMON109; FoodEx2 maintenance 2023 and 2024 F33 mapping updates -->
## Use Only When Additives Or Flavourings Context Is Active

- This page is a conditional domain overlay. Use it when the request, reporting context, legal reference, parameter hierarchy, or candidate collection indicates food additives or food flavourings monitoring.
- Typical activation signals include additives, flavourings, Regulation (EC) No 1333/2008, Part E of Annex II, `ADD`, `FLAV`, `addAnalysis`, `flavAnalysis`, or an additive/flavouring-domain FoodEx2 candidate set.
- Do not add additive or flavouring legislative facets to ordinary all-domain FoodEx2 coding unless the domain is active.

## F33 Legislative Class

- Additives and flavourings monitoring requires the relevant `F33 Legislative-classes` descriptor.
- If the selected base term already carries the required additive or flavouring `F33` implicitly, do not add the same `F33` explicitly. ChemMon warns against duplicating an implicit additive/flavouring `F33`.
- If the selected base term does not carry the required `F33` implicitly, add it explicitly.
- The generic legislative descriptor for all categories of foods is not allowed as the reported category.

## Additional Facets

- `F03 Physical-state` should be considered, and is highly recommended in several additive/flavouring categories when not implicit.
- `F23 Target-consumer` should be added for products formulated for infants under 12 months when the target consumer is not implicit.
- These extra facets are domain overlays. They do not change the ordinary rule that facets must refine the chosen FoodEx2 base term and respect syntax and cardinality constraints.

## Matrix Terms Not To Report As The Sample

- The following additive/flavouring substance or preparation terms should not be reported as `sampMatCode` for additive or flavouring result reporting: `A047N`, `A047Q`, `A047R`, `A047A`, `A047P`, and `A0F3T`.
- Choose the food matrix that contains the additive or flavouring, then add the legislative class facet when required.

## Worked Signals

- Red wine in an additives/flavourings context can be valid as the base term alone when its additive/flavouring legislative class is implicit.
- A soft-ripened cheese in an additives context may need explicit `F03` and `F33` if those are not already implicit.
- A vitamin supplement in an additives context may need physical-state and additive legislative class facets; the substance term itself is not the food matrix.

## Relevant Policy

- [[facet-coding-rules]] gives the ordinary facet-selection rule; this page identifies when additives/flavourings reporting makes `F33`, `F03`, or `F23` operationally important.
- [[implicit-vs-explicit-facets]] controls duplication: required `F33` does not mean repeat an implicit `F33`.
- [[domain-specific-validation]] contains the validation checks for mandatory additive and flavouring legislative categories.

