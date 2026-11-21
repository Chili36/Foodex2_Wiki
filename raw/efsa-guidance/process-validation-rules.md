---
title: "Process Validation Rules"
select_when: >-
  If the constructed code will carry any process facet — a treatment,
  preservation, or physical step — its validation needs these rules: how to
  check process ordCodes, process detail
  implicit in a derivative base versus explicitly stated, forbidden
  derivative-creating processes on raw bases, and reconstitution limits.
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2016 -  - FoodEx2 annual maintenance 2015.pdf"
related:
  - "[[business-rules]]"
  - "[[process-facets]]"
  - "[[term-type-facet-constraints]]"
  - "[[validation-rules]]"
last_updated: "2026-09-11"
---

# Process Validation Rules

## Process Coding and Validation

- Preserve every process stated by the sample through the base term or justified explicit facets. Do not discard processing information to satisfy a guessed ordinal restriction.
- Use the applicable active process rules below. Ordinals are root-scoped catalogue data, not categories to infer from a process label.
- BR26 is inactive in the observed ICT call path. It is background implementation information in [[business-rules]], not a default coding gate. Do not demand a BR26 check or report a routine BR26 deferral.

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28; docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table -->
## Main Process Rules

- `BR16`: an explicit process should not be less specific than the process already implicit in the base term. Check the underlying implicit-process logic in [[process-facets]]. (Business Rules `BR16`)
- `BR19`: raw commodities cannot take processes that create a derivative; pick the derivative base term instead, following [[base-term-selection]]. Official BR19 coverage comes from `BR_Data.csv`, but the sibling validator may emit transparent `BR19+` warnings from `BR_Data.extension.csv` for clear data-freshness gaps. (Business Rules `BR19`)
- A `BR19` rejection proves that the explicit process is invalid on that raw base; it does not prove that every nearby derivative candidate covers the product. For marketed-dry spices and herbal infusion materials, the correct repair can be to keep the raw base and remove redundant drying. Read the candidate scope and the exception in [[base-term-selection]] before switching bases. (EFSA guidance p42-43; 2015 maintenance p15)
- `BR26`: inactive in observed ICT; only consider the sibling implementation when the workflow explicitly requires that local check. See [[business-rules]] for the implementation distinction.
- `BR27`: at least two distinct non-integer ordinals in the same root-scoped integer family (`1`, `2`, ...) conflict only when that family contains an explicit process; implicit-only families and equal decimal values alone do not trigger BR27. These conflicts represent alternative derivative paths. Use ordinals from the base term's single applicable `BR_Data.csv` warn group. A validator result must also satisfy this distinct-value and explicit-process condition. If those values or a result verified against these conditions are unavailable, leave BR27 unverified rather than infer the result. The term-type consequences of those choices are summarised in [[term-type-facet-constraints]]. (Business Rules `BR27`)
- `BR28`: reconstitution or dilution cannot be added to already dehydrated, dried, powdered, or concentrated products; use the reconstituted product term instead. (Business Rules `BR28`)

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28 -->
## Worked Examples

- Before: dried fruit base + a broader preserving facet. After: invalid, `BR16`, because the explicit process is less detailed than the implicit one. (Business Rules `BR16`)
- Before: cereal grains + flaking process on a raw base. After: invalid, `BR19`; use the flaked cereal derivative. (Business Rules `BR19`)
- Before: a derivative with two explicit processes. After: retain the sample information, check applicable active rules, and use root-scoped evidence for BR27 when relevant. Do not reject the combination because of a guessed BR26 conflict. (Business Rules `BR27`; [[business-rules]] implementation status)

## Relevant Policy

- [[policy-contract]] `C03`, `C04`, and `C08` explain the policy side of these checks: do not rebuild derivative foods from raw plus `F28`, do not repeat implicit process, and keep only justified explicit process detail.
- [[policy-contract]] `R-PROC-001`, `R-PROC-002`, `R-PROC-003`, and `AP-001`: preserve stated processes, respect implicit specificity, use evidence for applicable active validation, and do not reconstruct standard derivatives as raw-plus-`F28`.

## Relevant Business Rules

- `BR16`: explicit process detail cannot be broader than the implicit process. See [[business-rules]].
- `BR19`: forbidden derivative-creating processes on raw commodities, including transparent `BR19+` extension warnings where configured. See [[business-rules]].
- `BR27`: active decimal-process check. BR26 is inactive in observed ICT and is not a default coding requirement. See [[business-rules]].
- `BR28`: reconstitution restrictions on dried, powdered, or concentrated products. See [[business-rules]].
