---
title: "FoodEx2 In Chemical Monitoring"
select_when: >-
  The case is reported under a chemical-monitoring data collection and needs
  the reporting overlay that sits on top of ordinary coding: how sampling
  detail, mandatory explicit facets, and legislative grouping change once a
  monitoring domain such as pesticides, contaminants, veterinary residues, or
  additives is in scope.
sources:
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "Guidance VMPR mapping to legislative products.pdf"
  - "EFSA Supporting Publications - 2022 -  - FoodEx2 maintenance 2021.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[pesticides-foodex2]]"
  - "[[contaminants-foodex2]]"
  - "[[domoic-acid-scallops]]"
  - "[[vmpr-foodex2]]"
  - "[[additives-flavourings-foodex2]]"
  - "[[maintenance-2024]]"
  - "[[domain-specific-validation]]"
  - "[[vmpr-legislative-mapping]]"
last_updated: "2026-06-10"
---

# FoodEx2 In Chemical Monitoring

<!-- Source: EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf p33-36; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33-36 -->
## Scope

- ChemMon does not redefine FoodEx2. It adds reporting constraints for chemical-monitoring workflows. Use this page as a domain-specific overlay, not as the core coding model described in [[foodex2-overview]]. (ChemMon 2025 p33-36; ChemMon 2026 p33-36)
- Samples are coded from the MTX reporting hierarchy at the lowest useful level of detail. (ChemMon 2025 p33)
- Domain overlays are conditional. Apply pesticide, contaminants, VMPR, additives, or flavourings rules only when the reporting domain is explicit, the parameter/legal context identifies it, or the candidate universe has already been filtered to that domain. (ChemMon 2026 FoodEx2 mapping and reporting flags sections)

## Domain Pages

- Use [[pesticides-foodex2]] for pesticide residue monitoring, Regulation (EC) No 396/2005, `PEST`, `pestParam`, or `MATRIX` contexts.
- Use [[contaminants-foodex2]] for contaminants or occurrence monitoring, `OCC`, `chemAnalysis`, acrylamide, domoic acid, pyrrolizidine alkaloids, metals, packaging migrants, and similar contaminant contexts.
- Use [[domoic-acid-scallops]] when the contaminant is domoic acid and the matrix is scallop; that overlay carries the source-provided `sampMatCode` / `sampMatText` lookup and the `origFishAreaCode` recommendation.
- Use [[vmpr-foodex2]] for veterinary medicinal product residues, `VMPR`, `VETDRUG`, `vmprParam`, `vmprCls`, VetDrugRes, and Plan 3 contexts.
- Use [[additives-flavourings-foodex2]] for additive and flavouring monitoring, `ADD`, `FLAV`, `addAnalysis`, `flavAnalysis`, and Regulation (EC) No 1333/2008 contexts.
- If no reporting domain is known, stay with all-domain FoodEx2 pages and the returned candidate list. Do not guess a domain from the food name alone.

## General Rules

- A base term is always mandatory. If implicit facets are enough, a base-term-only code is valid. The baseline rule set for that is still [[facet-coding-rules]]. (ChemMon 2025 p33; ChemMon 2026 p33)
- Explicit facets should only add information not already covered by implicit facets. The default logic is the same as [[implicit-vs-explicit-facets]], even when ChemMon later adds reporting exceptions. (ChemMon 2025 p33; ChemMon 2026 p33)
- For downstream legal grouping, EFSA uses both base terms and facets, including implicit ones. (ChemMon 2025 p33)

## VMPR-Specific Rules

- For VMPR, `F01 Source` and `F02 Part-nature` must be present, except for the feed/water and processed-composite cases described by ChemMon. That overlays the normal term-type rules in [[term-type-facet-constraints]]. (ChemMon 2025 p33-36; ChemMon 2026 p33-36)
- For processed derivatives under VMPR, `F01` may need to be added explicitly because it is not always implicit on processed terms such as dried egg or milk powder. This is a ChemMon exception to the default implicit logic in [[implicit-vs-explicit-facets]]. (ChemMon 2025 p33; ChemMon 2026 p33)
- Wild-animal VMPR samples require `F21.A07RY` (`Wild, gathered or hunted`). In the downstream ETL mapping this sets `Wild=1`, and that wild route supersedes the ordinary game route in the final legislative grouping. See [[vmpr-legislative-mapping]]. (ChemMon 2025 p34; ChemMon 2026 p33; VMPR mapping p5-6)
- Feed and water VMPR coding depends on `F23 Target-consumer`; conflicting explicit `F23` values can force classification to `Other`. (ChemMon 2025 p34-36; ChemMon 2026 p33-36)
- Non-food animal matrices use the generic base term `A0C60` plus explicit `F02` and `F01`; this includes non-food VMPR biological samples such as urine, retina, hair, blood, blood serum, and plasma. Whole blood remains a structural grey area because FoodEx2 also has food-chain blood terms; see [[vmpr-foodex2]] for the context-dependent boundary. (ChemMon 2025 p36; ChemMon 2026 p36; FoodEx2 maintenance 2021 p2, p10)
- `F33 Legislative-classes` is also important for VMPR processed products and for additives/flavourings workflows. In VMPR it is one of the classifier inputs EFSA uses downstream for legislative matrix assignment, not just a validation check. The corresponding blocking checks live in [[domain-specific-validation]], and the mapping flow is summarised in [[vmpr-legislative-mapping]]. (ChemMon 2025 CHEMON91-93; ChemMon 2026 CHEMON91-93; VMPR mapping p4-6)
- EFSA's downstream VMPR mapping derives `Game`, `Wild`, `FoodClassVMPR`, and `FoodClassVMPR_report` from the final `sampMatCode`. In that layer, `F21.A07RY`, `F23`, `F20.A0F4V`, and explicit `F33` can change the legislative outcome even when the FoodEx2 code already passes normal syntax checks. See [[vmpr-legislative-mapping]]. (VMPR mapping p3-6)

## Worked Examples

- Before: feed for pigs. After: `A0BBB#F23.A07VC`. This keeps the feed sample out of the generic `Other` bucket. (ChemMon 2025 p34-35; ChemMon 2026 p34-35)
- Before: cow hair sample. After: `A0C60#F02.A0ESP$F01.A057E`. ChemMon expects explicit source and part-nature for this non-food case, even though the generic-base strategy still follows [[facet-coding-rules]]. (ChemMon 2025 p36; ChemMon 2026 p36)
- Before: sheep blood serum sample in VMPR. After: `A0C60#F01.A0CDE$F02.A0CEY`. ChemMon treats this as a non-food animal-related matrix, not an edible blood commodity. (ChemMon 2025 p36; ChemMon 2026 p36)
- Before: animal plasma sample in VMPR. After: `A0C60` plus explicit `F01` source animal and `F02.A0CEX` plasma. In active VMPR biological-sample rows, blood-related matrices follow the non-food matrix rule unless the row explicitly describes an edible blood product or ingredient. (ChemMon 2025 p36; ChemMon 2026 p36)
- Before: wild deer fresh meat in VMPR. After: `A01SA#F21.A07RY`. The wild-production method must be added explicitly. (ChemMon 2026 lines around sample examples)
- Before: acrylamide result on french fries with no legislative class. After: `A0BYV#F33.A169H`. CHEMMON12 requires explicit `F33` for acrylamide (paramCode `RF-00000410-ORG`) even when the base term already carries an implicit `F33`. The acrylamide legislative class `A169H` maps to "AC-1.1 French fries from fresh potatoes" under Commission Regulation (EU) 2017/2158; this is one of the explicit exceptions noted in [[implicit-vs-explicit-facets]]. (ChemMon 2026; CHEMMON12)

## Relevant Policy

- [[policy-contract]] `C01`, `C07`, and `C08` still govern the coding core here: choose the right food type and facet family first, then add only the domain-mandated explicit descriptors.
- [[policy-contract]] Decision Procedure step 5 is the main handoff point for this page. Use it as a domain overlay after ordinary FoodEx2 coding structure is in place, not instead of it.

## Relevant Business Rules

- `BR14` and `BR15`: contextual validation paths activate only in the relevant reporting workflows. See [[business-rules]].
- `BR25`: domain-mandated explicit facets still have to respect single-cardinality limits. See [[business-rules]].
- `BR20` and `BR21`: deprecated or dismissed terms remain invalid even in ChemMon workflows. See [[business-rules]].
