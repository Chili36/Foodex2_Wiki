---
title: "FoodEx2 Maintenance 2025"
source_tier: "authoritative_rule"
sources:
  - "EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf"
related:
  - "[[maintenance-history]]"
  - "[[maintenance-2024]]"
  - "[[facet-coding-rules]]"
  - "[[process-facets]]"
  - "[[additives-flavourings-foodex2]]"
  - "[[pesticides-foodex2]]"
  - "[[base-term-selection]]"
last_updated: "2026-10-01"
---

# Maintenance 2025

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p1-6, p17-18 -->
## Summary And Release Context

- EFSA's ninth maintenance cycle covers MTX 16.1, 16.2 and 16.3 in 2025 and MTX 17.0 in January 2026, starting from MTX 16.0. The report was approved on 1 April 2026 and published on 9 April 2026 as EN-10069, DOI [10.2903/sp.efsa.2026.EN-10069](https://doi.org/10.2903/sp.efsa.2026.EN-10069). It is distinct from maintenance 2024, published in 2025. (2025 maintenance p1-6)
- The cycle added 79 new catalogue terms and updated 358 scope notes. Five terms lost reportability in particular hierarchies/facets; no terms were deprecated. A term can participate in several facets, so facet-specific counts below overlap. (2025 maintenance p17-18)
- This is an authoritative historical change record for the stated releases. Use current catalogue candidates, hierarchy membership and validator results for an actual code; this report does not establish the latest catalogue state.

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p7-10, p12-17 -->
## Main Changes

| Area | Change and coding consequence |
| --- | --- |
| Avian influenza | 32 bird taxonomic entries were added in F01: one order, one family, six genera, three species and 21 subspecies. Names, Euring attributes and parent links were revised; 340 bird scope notes were updated. These are not 32 new species. |
| One Health | 13 mammal terms were added in F01/F34, plus `F21.A1B1W Domesticated` for household-raised domestic animals. |
| NORA novel-food project | Ten source-organism terms were added under plants, fungi and marine algae. Their presence as F01 sources does not establish food-base reportability. |
| F01 and F34 | F01 gained 55 terms; F34 gained 45 bird/mammal terms. Parent relationships changed for 29 terms in each of these facet hierarchies. |
| EU Food Composition Database | Vegan/vegetarian target-consumer descriptors and three cooking-process descriptors were added. Use [[facet-coding-rules]] and [[process-facets]] for the operational distinctions. |
| F02 biological samples | `A1B1E Multiple organs/tissues (as part-nature)` describes a mixture of organs/tissues from the same animal; `A16XT Organ/tissue (zoonoses)` received clarified scope notes. |
| Additives/flavourings | Four F33 classes were added, ten class names revised and 21 base terms' implicit F33 mappings changed. Iced tea received a dedicated base mapped to `A0C1T FA-14.1.4 Flavoured drinks`; bitter liqueur received a base under herb liqueur. Four F03 descriptors distinguish supplement forms. See [[additives-flavourings-foodex2]]. |
| Pesticides | Six existing terms received matrix codes, one lost its matrix code, and small versus large radish leaves were distinguished. Small radish leaves are present but not reportable in PRIMo. See [[pesticides-foodex2]]. |
| F31 bird age | Four descriptors under `A0C8K Age classes for birds` distinguish under/over 12 weeks and under/over 16 weeks for chemical monitoring. Choose the catalogue-confirmed descriptor matching known age and reporting requirements. |

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p7, p10, p14, Tables 3-4 -->
## Placement And Process Interpretation

- `A18TH Tropical root and tuber vegetable dishes` moved under `A03VC Dishes excluding pasta or rice dishes, sandwiches and pizza` in its reportable hierarchies, including Reporting and Exposure.
- `A18BB Cheese, neufchatel` moved under `A02RT Soft-ripened cheese with bloomy rind (white mould) (brie, camembert type)` in its reportable hierarchies.
- `A035M Chewing gum` moved under `A04PE Confectionery including chocolate`, rather than the soft-candies subcategory.
- `A07GK Scalding` and `A07GQ Pressure cooking` became core process terms directly under `A0BA1 Cooking and similar thermal preparation processes`. Do not infer their current placement from the old water-cooking/steaming groupings.
- LanguaL mappings changed to `G0023` for `A07GP Steaming without pressure` and `G0040` for `A07HH Reheating in the pack`.

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p15, p17, Table 6 -->
## Reportability Changes

| Term | No longer reportable in | Consequence |
| --- | --- | --- |
| `A03PX Food for infants and young children` | Reporting | Choose a suitable reportable, more specific food base; see [[base-term-selection]]. |
| `A0C5V FA-0. All categories of foods` | F33 Legislative-classes | Use the applicable specific legislative class. |
| `A1A9M Farrow-to-finish` | F21 Production-method | Reportable in F29 Purpose-of-raising for the pig/MRSA/SIGMA context. |
| `A1A9N Weaner-to-finish` | F21 Production-method | Reportable in F29 Purpose-of-raising for the pig/MRSA/SIGMA context. |
| `A1A9P Finisher` | F21 Production-method | Reportable in F29 Purpose-of-raising for the pig/MRSA/SIGMA context. |

Dismissal in one hierarchy is not global deprecation. The F21-to-F29 change is a concrete example. Keep any returned blocking validation result; resolve discrepancies against the intended hierarchy and imported catalogue data as described in [[business-rules]].

<!-- Source: EFSA Supporting Publications - 2026 -  - FoodEx2 maintenance 2025.pdf p18, p21 -->
## Source Scope

The 21-page PDF is retained as the source. Appendix A (the full change spreadsheet) and Appendix B (the MTX 17.0 catalogue spreadsheet) are separate supplementary files, not tables embedded in the PDF. This page captures the report's stated changes, not every supplemental row or an exhaustive catalogue import.

## Relevant Policy

- [[policy-contract]] `C05` and `C09`: use release history to understand catalogue changes, then check current candidate scope and reportability; historical states do not override current higher-priority evidence.
- [[policy-contract]] `C08` and `C10`: do not repeat implicit facets, and activate reporting-domain requirements only in the relevant domain.

## Relevant Business Rules

- `BR20` and `BR21`: distinguish global deprecation from hierarchy-specific dismissal while preserving blocking validator results. See [[business-rules]].
- `BR17`, `BR23` and `BR24`: a facet or unsuitable hierarchy term is not a valid food base. See [[business-rules]].
- `BR30` and `BR31`: explicit facets must use the correct category and descriptor membership, particularly after the F21/F29 change. See [[business-rules]].
