---
title: "Process Validation Rules"
select_when: >-
  If the constructed code will carry any process facet — a treatment,
  preservation, or physical step — its validation needs these rules: which
  processes may combine (mutually exclusive ordinal groups), process detail
  implicit in a derivative base versus explicitly stated, forbidden
  derivative-creating processes on raw bases, and reconstitution limits.
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
related:
  - "[[business-rules]]"
  - "[[process-facets]]"
  - "[[term-type-facet-constraints]]"
  - "[[validation-rules]]"
last_updated: "2026-06-07"
---

# Process Validation Rules

<!-- Source: BUSINESS-RULES-COMPACT.json processOrdinalGroups; BUSINESS-RULES.md BR26, BR27 -->
## Ordinal Groups

| Ordinal group | Meaning | Rule |
| --- | --- | --- |
| `1.x` | Heating methods | Mutually exclusive within the group |
| `2.x` | Preservation | Mutually exclusive within the group |
| `3.x` | Physical treatments | Mutually exclusive within the group |
| `0` | Non-exclusive processes | Can coexist with other groups |

- Process ordinals are the intended mechanism for detecting incompatible process combinations. Same-group alternatives should not be stacked just because both are technically `F28` facets. (Compact JSON; `BR26-BR27`)
- Validator-status caveat: `BR26` is a known divergence. In the observed ICT source it is effectively silent, and the sibling validator is also effectively silent for BR26 until its derivative ordinal lookup is fixed. Keep the semantic guidance, but do not assume the validator will always flag same-ordinal combinations. (Business Rules `BR26`)

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28; docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table -->
## Main Process Rules

- `BR16`: an explicit process should not be less specific than the process already implicit in the base term. Check the underlying implicit-process logic in [[process-facets]]. (Business Rules `BR16`)
- `BR19`: raw commodities cannot take processes that create a derivative; pick the derivative base term instead, following [[base-term-selection]]. Official BR19 coverage comes from `BR_Data.csv`, but the sibling validator may emit transparent `BR19+` warnings from `BR_Data.extension.csv` for clear data-freshness gaps. (Business Rules `BR19`)
- `BR26`: two processes from the same ordinal group conflict semantically, but current validators can be silent because of the known divergence described in [[business-rules]]. (Business Rules `BR26`)
- `BR27`: decimal ordinals in the same process family also conflict; they represent alternative derivative paths. The term-type consequences of those choices are summarised in [[term-type-facet-constraints]]. (Business Rules `BR27`)
- `BR28`: reconstitution or dilution cannot be added to already dehydrated, dried, powdered, or concentrated products; use the reconstituted product term instead. (Business Rules `BR28`)

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28 -->
## Worked Examples

- Before: dried fruit base + a broader preserving facet. After: invalid, `BR16`, because the explicit process is less detailed than the implicit one. (Business Rules `BR16`)
- Before: cereal grains + flaking process on a raw base. After: invalid, `BR19`; use the flaked cereal derivative. (Business Rules `BR19`)
- Before: one derivative with two `F28` codes from the same ordinal family. After: treat as a process-composition risk; `BR27` can still flag decimal-family conflicts, while `BR26` may be silent until the validator divergence is fixed. (Business Rules `BR26-BR27`)

## Relevant Policy

- [[policy-contract]] `C03`, `C04`, and `C08` explain the policy side of these checks: do not rebuild derivative foods from raw plus `F28`, do not repeat implicit process, and keep only justified explicit process detail.
- [[policy-contract]] `R-PROC-001`, `R-PROC-002`, and `AP-001` are the nearest policy rules: process choices must respect ordinal grouping, implicit specificity, and the ban on raw-plus-`F28` reconstruction of standard derivatives.

## Relevant Business Rules

- `BR16`: explicit process detail cannot be broader than the implicit process. See [[business-rules]].
- `BR19`: forbidden derivative-creating processes on raw commodities, including transparent `BR19+` extension warnings where configured. See [[business-rules]].
- `BR26` and `BR27`: process ordinal conflicts; BR26 currently has a known validator-silence divergence. See [[business-rules]].
- `BR28`: reconstitution restrictions on dried, powdered, or concentrated products. See [[business-rules]].
