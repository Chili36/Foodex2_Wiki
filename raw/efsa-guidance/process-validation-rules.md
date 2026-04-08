---
title: "Process Validation Rules"
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
related:
  - "[[process-facets]]"
  - "[[term-type-facet-constraints]]"
  - "[[validation-rules]]"
last_updated: "2026-04-08"
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

- The validator uses process ordinals to detect incompatible combinations. Same-group alternatives cannot be stacked just because both are technically `F28` facets. (Compact JSON; `BR26-BR27`)

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28; docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table -->
## Main Process Rules

- `BR16`: an explicit process should not be less specific than the process already implicit in the base term. Check the underlying implicit-process logic in [[process-facets]]. (Business Rules `BR16`)
- `BR19`: raw commodities cannot take processes that create a derivative; pick the derivative base term instead, following [[base-term-selection]]. (Business Rules `BR19`)
- `BR26`: two processes from the same ordinal group conflict. (Business Rules `BR26`)
- `BR27`: decimal ordinals in the same process family also conflict; they represent alternative derivative paths. The term-type consequences of those choices are summarised in [[term-type-facet-constraints]]. (Business Rules `BR27`)
- `BR28`: reconstitution or dilution cannot be added to already dehydrated, dried, powdered, or concentrated products; use the reconstituted product term instead. (Business Rules `BR28`)

<!-- Source: BUSINESS-RULES.md BR16, BR19, BR26, BR27, BR28 -->
## Worked Examples

- Before: dried fruit base + a broader preserving facet. After: invalid, `BR16`, because the explicit process is less detailed than the implicit one. (Business Rules `BR16`)
- Before: cereal grains + flaking process on a raw base. After: invalid, `BR19`; use the flaked cereal derivative. (Business Rules `BR19`)
- Before: one derivative with two `F28` codes from the same ordinal family. After: invalid, `BR26` or `BR27`, depending on whether the conflict is integer-level or decimal-level. (Business Rules `BR26-BR27`)
