---
title: "FoodEx2 In Additives And Flavourings Monitoring"
select_when: >-
  The case is reported under food additives or flavourings monitoring, where
  the relevant legislative-class facet is required unless already implicit,
  supplement form and beverage identity can change the applicable class,
  physical-state and target-consumer facets are recommended, and certain
  substance or preparation terms must not be reported as the sample matrix.
sources:
  - "EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf"
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
  - "[[maintenance-2025]]"
last_updated: "2026-10-01"
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

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p10-11, p16-17 -->
## Catalogue Changes Affecting Class Selection

- Maintenance 2025 revised the implicit additive F33 mapping of 21 base terms. Inspect the selected candidate's current implicit facets before adding a class; an older mapping may no longer apply. (2025 maintenance p10)
- The dedicated `Iced tea` base was introduced to avoid inconsistent classification and maps to `A0C1T FA-14.1.4 Flavoured drinks`. When that catalogue candidate fits the beverage, use its identity and implicit mapping; do not assume every tea-named drink belongs to the ordinary tea/infusion legislative class. (2025 maintenance p10-11)
- `A0C5V FA-0. All categories of foods` was made non-reportable in F33. Four classes were added: three under `A0C13 FA-18` and one for milk-based drinks and similar products intended for young children under `A0C5T FA-01`. Ten class names were revised, including the specific-group food categories. Use current class scope, not an old display label. (2025 maintenance p16-17)
- For supplements, distinguish the known physical form using `F03.A1B1N Effervescent tablets`, `F03.A1B1X Chewable tablets`, `F03.A1B1O Drops` or `F03.A1B1Y Syrup-type` when that detail is not implicit. Tablets are under `A06JH`; drops and syrup-type under `A06JL Liquid`. Additive limits can depend on form, but adding these descriptors is not a new universal requirement for every food. (2025 maintenance p10, p13)

## Additional Facets

- `F03 Physical-state` should be considered for the following legislative categories and is highly recommended when not already implicit. This is a scoped recommendation, not a universal mandatory facet. (ChemMon 2026 p38-39)

| Legislative category | Scope |
| --- | --- |
| 1 | Dairy products and analogues |
| 6.3 | Breakfast cereals |
| 12.5 | Soups and broths |
| 12.6 | Sauces |
| 13 | Foods intended for specific groups under Regulation (EU) No 609/2013 |
| 14.1.2 | Fruit juices and vegetable juices |
| 14.1.3 | Fruit nectars, vegetable nectars and similar products |
| 14.1.4 | Flavoured drinks |
| 14.1.5 | Coffee/extracts, tea, herbal/fruit infusions, coffee substitutes and hot-beverage mixes |
| 17 | Food supplements, excluding supplements for infants and young children |

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
- [[policy-contract]] `C08` and `C10`: avoid redundant facets and keep additive/flavouring obligations conditional on that reporting domain.

## Relevant Business Rules

- `BR21`: respect returned dismissal errors and the intended hierarchy's reportability. See [[business-rules]].
- `BR25`, `BR30` and `BR31`: respect facet cardinality, valid category syntax and descriptor membership. See [[business-rules]].
