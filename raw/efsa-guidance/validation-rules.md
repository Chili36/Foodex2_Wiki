---
title: "Validation Rules Overview"
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
related:
  - "[[structural-validation]]"
  - "[[term-type-facet-constraints]]"
  - "[[process-validation-rules]]"
  - "[[domain-specific-validation]]"
  - "[[code-string-format]]"
last_updated: "2026-04-05"
---

# Validation Rules Overview

<!-- Source: docs/VALIDATION_RULES_SUMMARY.md Overview, Validation Layers; BUSINESS-RULES.md Overview -->
## Two Validation Layers

- The validator runs structural checks first, then business rules. Structural checks cover syntax, facet parsing, descriptor lookup, implicit-facet cleanup, and duplicate/cardinality issues. Business rules then apply `BR01-BR31` to term type, hierarchy, process, and lifecycle constraints. (Validation Rules Summary; Business Rules Overview)
- A code can be syntactically clean but still fail policy rules such as `BR03`, `BR17`, or `BR20`. See [[structural-validation]] and [[term-type-facet-constraints]]. (Validation Rules Summary)

<!-- Source: BUSINESS-RULES.md Severity Classification Overview; BUSINESS-RULES-COMPACT.json ruleSeverities -->
## Severity Model

| Severity | Effect | Typical rules |
| --- | --- | --- |
| `ERROR` | Validation fails immediately | `BR29-BR31` |
| `HIGH` | Hard warning treated as invalid | `BR01`, `BR03-BR08`, `BR13`, `BR16-BR17`, `BR19-BR21`, `BR24-BR28` |
| `LOW` | Advisory only | `BR10-BR12`, `BR15`, `BR23` |
| `NONE` | Informational only | `BR22` |

- `BR02`, `BR09`, and `BR18` are placeholders and are not currently implemented. (Business Rules Overview; Compact JSON)

<!-- Source: docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table; BUSINESS-RULES.md BR03, BR04, BR17, BR20, BR21, BR29, BR30, BR31 -->
## High-Impact Blocking Rules

- `BR03` and `BR04`: composite foods cannot use `F01` or `F27`; use `F04 ingredient` instead. See [[term-type-facet-constraints]]. (Business Rules `BR03-BR04`)
- `BR17`: a facet term can never be the base term. (Business Rules `BR17`)
- `BR20` and `BR21`: deprecated and dismissed terms are always invalid, even if the code string is well formed. (Business Rules `BR20-BR21`)
- `BR29-BR31`: the code must use valid syntax, a real facet category, and a descriptor that belongs to that category. See [[structural-validation]]. (Business Rules `BR29-BR31`)

<!-- Source: docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table; BUSINESS-RULES.md Validation Examples -->
## Worked Examples

- Before: `A0B9Z`. After: valid base-only code. A facet is not required when the base term already fits. (Business Rules Validation Examples)
- Before: `A000J#F01.A0F6E`. After: invalid, `BR03`. Composite terms cannot use `F01 source`. (Business Rules `BR03`)
- Before: `A0B9Z#F99.A07JS`. After: invalid, `BR30`. `F99` is not a valid facet category. (Business Rules `BR30`)
