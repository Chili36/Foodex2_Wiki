---
title: "FoodEx2 In Chemical Monitoring"
sources:
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2024]]"
last_updated: "2026-04-05"
---

# FoodEx2 In Chemical Monitoring

<!-- Source: EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf p33-36; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33-36 -->
## Scope

- ChemMon does not redefine FoodEx2. It adds reporting constraints for chemical-monitoring workflows. Use this page as a domain-specific overlay, not as the core coding model. (ChemMon 2025 p33-36; ChemMon 2026 p33-36)
- Samples are coded from the MTX reporting hierarchy at the lowest useful level of detail. (ChemMon 2025 p33)

## General Rules

- A base term is always mandatory. If implicit facets are enough, a base-term-only code is valid. (ChemMon 2025 p33; ChemMon 2026 p33)
- Explicit facets should only add information not already covered by implicit facets. (ChemMon 2025 p33; ChemMon 2026 p33)
- For downstream legal grouping, EFSA uses both base terms and facets, including implicit ones. (ChemMon 2025 p33)

## VMPR-Specific Rules

- For VMPR, `F01 Source` and `F02 Part-nature` must be present, except for the feed/water and processed-composite cases described by ChemMon. (ChemMon 2025 p33-36; ChemMon 2026 p33-36)
- For processed derivatives under VMPR, `F01` may need to be added explicitly because it is not always implicit on processed terms such as dried egg or milk powder. (ChemMon 2025 p33; ChemMon 2026 p33)
- Wild-animal VMPR samples require `F21.A07RY` (`Wild, gathered or hunted`). (ChemMon 2025 p34; ChemMon 2026 p33)
- Feed and water VMPR coding depends on `F23 Target-consumer`; conflicting explicit `F23` values can force classification to `Other`. (ChemMon 2025 p34-36; ChemMon 2026 p33-36)
- Non-food animal matrices use the generic base term `A0C60` plus explicit `F02` and `F01`. (ChemMon 2025 p36; ChemMon 2026 p36)
- `F33 Legislative-classes` is also important for VMPR processed products and for additives/flavourings workflows. (ChemMon 2025 CHEMON91-93; ChemMon 2026 CHEMON91-93)

## Worked Examples

- Before: feed for pigs. After: `A0BBB#F23.A07VC`. This keeps the feed sample out of the generic `Other` bucket. (ChemMon 2025 p34-35; ChemMon 2026 p34-35)
- Before: cow hair sample. After: `A0C60#F02.A0ESP$F01.A057E`. ChemMon expects explicit source and part-nature for this non-food case. (ChemMon 2025 p36; ChemMon 2026 p36)
- Before: wild deer fresh meat in VMPR. After: `A01SA#F21.A07RY`. The wild-production method must be added explicitly. (ChemMon 2026 lines around sample examples)
- Before: acrylamide result on french fries with no legislative class. After: `A0BYV#F33.A169H`. CHEMMON12 requires explicit `F33` for acrylamide (paramCode `RF-00000410-ORG`) even when the base term already carries an implicit `F33`. The acrylamide legislative class `A169H` maps to "AC-1.1 French fries from fresh potatoes" under Commission Regulation (EU) 2017/2158. (ChemMon 2026; CHEMMON12)
