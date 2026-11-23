---
title: "FoodEx2 Maintenance 2020"
sources:
  - "EFSA Supporting Publications - 2021 -  - FoodEx2 maintenance 2020.pdf"
related:
  - "[[maintenance-history]]"
  - "[[maintenance-2019]]"
  - "[[maintenance-2021]]"
  - "[[base-term-selection]]"
last_updated: "2026-11-23"
---

# Maintenance 2020

<!-- Source: EFSA Supporting Publications - 2021 -  - FoodEx2 maintenance 2020.pdf p3, p6-16 -->
## Summary

- EFSA added 108 new terms in 2020. Major additions served MUST-B honey bees, avian-influenza birds, SIGMA age classes, scallop-part coding, botanicals, and OpenFoodTox. (2020 maintenance p3)
- 80 terms were dismissed in some hierarchies, and 40 were deprecated in total. Term type changed for 6 codes and detail level changed for 10 codes. (2020 maintenance p3)
- Implicit facets and hierarchy relationships were updated to stay consistent with FoodEx2 logic. (2020 maintenance p3)

## Dismissal Versus Deprecation

The source distinguishes dismissal (non-reportable in one or more hierarchies but still reportable in others) from deprecation (non-reportable in all hierarchies). These definitions are in the page-3 footnotes. Use current hierarchy/reportability data when coding, and retain the blocking validator behavior explained in [[business-rules]]; a historical definition is not permission to bypass BR21.

## Project-Driven Changes

- `F31 Animal-age-class` grew for SIGMA. (2020 maintenance p3, p10)
- `F20 Part-consumed-analysed` gained scallop descriptors for marine-biotoxin work. (2020 maintenance p3)
- The Exposure hierarchy was revised for Regulation (EU) 609/2013 alignment. (2020 maintenance p4, p10-11)
- Reporting and Exposure reportability diverged in this maintenance: 74 terms were dismissed from Exposure and 6 from Reporting (mostly sweetening and fortifying agents, which became facet-only in Exposure), and `A01QD` was set non-reportable in Exposure only. Revision 2's statement that the two hierarchies share the same reportable terms no longer holds; see [[base-term-selection]]. (2020 maintenance p13)

## Release Context

- Covers MTX 11.1, 11.2 and the January 2021 major release MTX 12.0. (2020 maintenance p3)

## Relevant Policy

- [[policy-contract]] `C05` applies directly: historical examples and older catalogue states do not override higher-priority current policy rules.
- [[policy-contract]] `C09` matters here as well: maintenance pages help explain current candidate coverage, term placement, and catalogue fit before a candidate is selected.

## Relevant Business Rules

- No single `BRxx` rule governs this historical page by itself.
- Use [[business-rules]] when a maintenance change affects reportability, deprecation, dismissal, hierarchy use, or facet applicability, especially `BR08`, `BR20`, `BR21`, `BR23`, and `BR24`.
