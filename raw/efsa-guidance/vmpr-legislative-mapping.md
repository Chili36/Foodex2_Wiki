---
title: "VMPR Legislative Mapping"
sources:
  - "Guidance VMPR mapping to legislative products.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[domain-specific-validation]]"
  - "[[maintenance-2024]]"
  - "[[facet-coding-rules]]"
last_updated: "2026-04-22"
---

# VMPR Legislative Mapping

<!-- Source: Guidance VMPR mapping to legislative products.pdf p3-6 -->
## Scope

- This page describes EFSA's downstream VMPR mapping from FoodEx2 `sampMatCode` values into legislative commodity outputs used in ETL processing and the LLDB. It does not replace ordinary FoodEx2 coding; code the sample first, then apply this mapping logic as a reporting-layer interpretation. (VMPR mapping p3-6)
- In VMPR, the allowed base terms are already restricted through the `VetDrugRes` hierarchy. This page explains what EFSA derives from that coded input afterwards, not how to escape the normal FoodEx2 base-term and facet model. See [[chemical-monitoring-foodex2]] and [[facet-coding-rules]]. (VMPR mapping p3)

## Mapping Stages

1. Create the `Game` flag from `F01 Source`.
2. Run the `FoodClassVMPR` classifier from the coded sample.
3. Create the `Wild` flag from `F21 Production-method`.
4. Derive the final legislative commodity in `FoodClassVMPR_report`.

The mapping order matters because later stages can supersede earlier ones. The downstream classifier is therefore procedural, not a flat lookup. (VMPR mapping p3-6)

## Game Flag

- `Game=1` when one of the designated game-source `F01` facets is present explicitly or implicitly in the coded sample. The list in the guidance includes `A056T` chamois, `A056V` moufflon, `A056X` hare, `A056Y` wild boar, `A056M` deer, `A0F2A` camelidae, `A0CTQ` peccari, `A0CSP` steinbock, `A16NY` musk ox, `A0CSY` struthioniformes, `A16CF` Barbary sheep, `A16DL` mountain goat, `A056L` game or wild mammals, `A169S` generic ruminants, and `A16BX` antelopes. (VMPR mapping p3-4)
- This flag is created from the coded FoodEx2 sample, not from a separate manual field. Because the mapping reads implicit as well as explicit source information, the ordinary FoodEx2 rule still applies: do not add redundant origin facets unless the VMPR workflow actually requires them. See [[implicit-vs-explicit-facets]] and [[domain-specific-validation]]. (VMPR mapping p4)

## FoodClassVMPR Classifier

- `FoodClassVMPR` is the intermediate LLDB classifier used to map coded samples to the matrices in Regulation (EU) No 37/2010 and the categories introduced by Regulation (EU) 2022/1646. It is a first-match-wins table, so coding detail that satisfies an earlier row will stop later fallback routes from being used. (VMPR mapping p4-5)
- The classifier reads `F01 Source`, `F02 Part-nature`, `F20 Part-consumed analysed` for meat-as-muscle (`A0F4V Excluding visible fat`), `F23 Target-consumer` for feed and water, and `F33 Legislative-classes` for processed products. These are not decorative descriptors in VMPR; they can change the legislative matrix assigned downstream. See [[chemical-monitoring-foodex2]] and [[domain-specific-validation]]. (VMPR mapping p4)
- Game samples are generally assigned to `M020A Other products` at this classifier stage, except for the ratite case noted by EFSA. That intermediate assignment can still be superseded later by the `Game` or `Wild` flags. (VMPR mapping p4)

## Wild Flag

- `Wild=1` when `F21.A07RY` (`Wild, gathered or hunted`) is present. This applies not only to game-source animals but also to fish or poultry explicitly reported as hunted. (VMPR mapping p5)
- In practice, this means `F21.A07RY` is operationally significant in VMPR. If the sample is wild or hunted and the explicit production method is omitted, the downstream VMPR mapping cannot promote the sample into the wild-game route. See [[chemical-monitoring-foodex2]]. (VMPR mapping p5)

## Final Legislative Commodity Mapping

- The final output column is `FoodClassVMPR_report`, filled from the `vmprCls` hierarchy. The mapping order is:
  1. if `Wild=1`, assign `MC008A Game (Wild Game)`
  2. else if `Game=1`, assign `MC007A Game (Farmed Game)`
  3. else map from the parent structure of `FoodClassVMPR`, with eggs and milk handled before the parent animal group (VMPR mapping p5-6)
- The explicit egg-first and milk-first exceptions matter because those products can otherwise inherit the parent animal group too early. The guidance maps egg-related rows to `MC002A Eggs` and milk or dairy rows to `MC001A Milk` before falling back to broader animal parents. (VMPR mapping p5-6)
- The remaining published parent routes include `MC003A Honey`, `MC005A Aquaculture`, `MC006A Bovines`, `MC009A Goats`, `MC010A Horses`, `MC011A Pigs`, `MC012A Poultry`, `MC013A Rabbits`, and `MC014A Sheep`, while `Casings`, `Insects`, and `Reptiles` keep their own dedicated outputs. In the VMPR EU Annual Report, sheep and goats are later considered together. (VMPR mapping p5-6)

## Practical Consequences For Coding

- `F21.A07RY` is not optional color in VMPR when the sample is wild or hunted. It drives the `Wild` flag, and `Wild` overrides the ordinary `Game` route in the final mapping. (VMPR mapping p5-6)
- `F33 Legislative-classes` on processed VMPR products is not only a validation artifact. It is one of the classifier inputs EFSA uses to decide the downstream legislative matrix. (VMPR mapping p4)
- `F23 Target-consumer` matters for feed and water, and `F20.A0F4V` matters for meat as muscle. If those details are present in the reporting context, omitting them can change the downstream VMPR classifier result even when the FoodEx2 code still looks superficially plausible. (VMPR mapping p4)
- This page is downstream reporting logic, not base-term policy. Use [[base-term-selection]] and [[facet-coding-rules]] to build the FoodEx2 code first; use this page to understand how EFSA later aggregates that code for VMPR legislation. (VMPR mapping p3-6)

## Relevant Policy

- [[policy-contract]] `C07` and `C08` govern this page indirectly: the downstream mapping depends on the correct facet family being used for the chosen food type and on avoiding redundant or misleading explicit facets.
- [[policy-contract]] Decision Procedure step 5 is the main hook here. This mapping is applied after the FoodEx2 code has already been composed, not instead of the ordinary coding workflow.

## Relevant Business Rules

- No single `BRxx` rule defines the VMPR legislative mapping itself; this page describes a downstream reporting classification layer rather than a validator-only constraint.
- `BR14` and `BR15`: the mapping only matters in the relevant reporting workflow. See [[business-rules]].
- `BR25`: mapping-relevant facet families still have to respect single-cardinality limits. See [[business-rules]].
- `BR29`, `BR30`, and `BR31`: malformed or non-existent facet strings cannot be interpreted correctly by the downstream mapping layer. See [[business-rules]].
