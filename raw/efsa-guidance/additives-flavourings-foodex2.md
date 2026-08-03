---
title: "FoodEx2 In Additives And Flavourings Monitoring"
select_when: >-
  The case is reported under food additives or flavourings monitoring, where
  the relevant legislative-class facet is required unless already implicit,
  physical-state is conditionally recommended, target-consumer may be needed, and certain
  substance or preparation terms must not be reported as the sample matrix.
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - FoodEx2 maintenance 2024.pdf"
  - "EFSA Supporting Publications - 2024 -  - FoodEx2 maintenance 2023.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2023]]"
  - "[[maintenance-2024]]"
last_updated: "2026-08-01"
---

# FoodEx2 In Additives And Flavourings Monitoring

<!-- Source: ChemMon 2026 food additives and flavourings section p38-39; ChemMon 2026 CHEMON86 and CHEMON109; ChemMon 2025 p38-39; FoodEx2 maintenance 2023 and 2024 F33 mapping updates -->
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

- Under ChemMon 2026, `F03 Physical-state` is not a universal additives/flavourings requirement. It should be considered for legislative categories `1`, `6.3`, `12.5`, `12.6`, `13`, `14.1.2`, `14.1.3`, `14.1.4`, `14.1.5`, and `17`; when not implicit in one of those categories, adding it explicitly is highly recommended rather than mandatory.
- Do not infer an `F03` requirement merely because a sample has an obvious physical state. Category `14.2.2` wine is outside the ChemMon 2026 list.
- `F23 Target-consumer` should be added for products formulated for infants under 12 months when the target consumer is not implicit.
- These extra facets are domain overlays. They do not change the ordinary rule that facets must refine the chosen FoodEx2 base term and respect syntax and cardinality constraints.

## Collection-Year Boundary

- ChemMon 2025 used broader wording that two facets should always be present and illustrated red wine as `A03MX#F03.A06JL` (explicit liquid), while still describing a missing `F03` as highly recommended rather than mandatory.
- ChemMon 2026 narrows physical-state guidance to the listed categories above. Its red-wine example gives `A03MX` as the correct code because the required `F33` for category `14.2.2` is implicit; it does not add explicit `F03`.
- Apply the guidance for the reporting collection year. Do not carry the 2025 wine example forward as a universal 2026 rule.

## Matrix Terms Not To Report As The Sample

- The following additive/flavouring substance or preparation terms should not be reported as `sampMatCode` for additive or flavouring result reporting: `A047N`, `A047Q`, `A047R`, `A047A`, `A047P`, and `A0F3T`.
- Choose the food matrix that contains the additive or flavouring, then add the legislative class facet when required.

## Worked Signals

- For 2026 reporting, red wine `A03MX` can be valid as the base term alone when its category `14.2.2` additive/flavouring `F33` is implicit; the official 2026 example does not add `F03`.
- A soft-ripened cheese in an additives context may need explicit `F03` and `F33` if those are not already implicit.
- A vitamin supplement in an additives context may need physical-state and additive legislative class facets; the substance term itself is not the food matrix.

## Relevant Policy

- [[facet-coding-rules]] gives the ordinary facet-selection rule; this page identifies when additives/flavourings reporting makes `F33`, `F03`, or `F23` operationally important.
- [[implicit-vs-explicit-facets]] controls duplication: required `F33` does not mean repeat an implicit `F33`.
- [[domain-specific-validation]] contains the validation checks for mandatory additive and flavouring legislative categories.
