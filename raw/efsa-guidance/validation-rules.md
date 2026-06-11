---
title: "Validation Rules Overview"
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
  - "FoodEx2 codification guidance_2025_12_v3.pdf"
related:
  - "[[business-rules]]"
  - "[[structural-validation]]"
  - "[[term-type-facet-constraints]]"
  - "[[process-validation-rules]]"
  - "[[domain-specific-validation]]"
  - "[[code-string-format]]"
last_updated: "2026-06-12"
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
- `BR13` is precise: it blocks seven disintegration-family `F03` descriptors on raw commodities, not all `F03` descriptors. (Business Rules `BR13`)
- `BR19+` warnings can appear in the sibling validator when transparent local extension rows cover BR19 root/process gaps left by the stale upstream `BR_Data.csv`. (Business Rules `BR19`)
- `BR26` has a known validator-silence divergence; process ordinal conflicts remain coding risks even when current validators do not emit BR26. (Business Rules `BR26`)

<!-- Source: docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table; BUSINESS-RULES.md BR03, BR04, BR17, BR20, BR21, BR29, BR30, BR31 -->
## High-Impact Blocking Rules

- `BR03` and `BR04`: composite foods cannot use `F01` or `F27`; use `F04 ingredient` instead. See [[term-type-facet-constraints]]. (Business Rules `BR03-BR04`)
- `BR17`: a facet term can never be the base term. (Business Rules `BR17`)
- `BR20` and `BR21`: deprecated and dismissed terms are always invalid, even if the code string is well formed. (Business Rules `BR20-BR21`)
- `BR29-BR31`: the code must use valid syntax, a real facet category, and a descriptor that belongs to that category. See [[structural-validation]]. (Business Rules `BR29-BR31`)

<!-- Source: FoodEx2 codification guidance_2025_12_v3.pdf p89-92 -->
## Practical Dataset Checks

These checks come from ANSES expert guidance and are useful for batch review. They are not replacements for the validator.

- Feed/food mismatches: feed entries should use feed terms, and food entries should not be coded with feed terms unless the source text genuinely identifies animal feed. (ANSES guidance p89)
- Hierarchy bases: filter for hierarchy detail levels used as base terms, then replace them with reportable non-hierarchy terms where the source detail allows it. (ANSES guidance p89)
- Raw base plus derivative-creating process: filter raw base terms with process facets such as milling, drying, curing, fermentation, pickling, canning/jarring, or smoking because a derivative base probably exists. See [[process-validation-rules]] for the validator side of this rule. (ANSES guidance p90)
- Flavouring review: check whether a flavoured product uses a food ingredient, a regulated flavouring, or both; incomplete ingredient reporting is common. See [[ingredient-facets]]. (ANSES guidance p91)
- Infusion ambiguity: check whether the code describes the dry infusion material or the final reconstituted beverage. (ANSES guidance p91)
- `F04` on raw or derivative bases: review whether it is a legitimate minor ingredient/coating/flavour, or whether the code incorrectly used `F04` where `F01` or `F27` should describe source. (ANSES guidance p92)
- Multiple `F01` sources on raw bases: same-nature mixed raw commodities should usually use multiple `F27 Source-commodities`, not multiple `F01 Source` descriptors. (ANSES guidance p92)

## Relevant Policy

- [[policy-contract]] Decision Procedure step 5 is the direct policy hook for this page: validation happens after food type, base term, and facet logic have already been resolved.
- [[policy-contract]] `R-SYNTAX-001`, `R-LENGTH-001`, and `R-FACET-001` explain the core policy expectations that the validator then checks structurally or through `BRxx` rules.

## Relevant Business Rules

- `BR03` and `BR04`: composites cannot use `F01` or `F27`. See [[business-rules]].
- `BR17`: facet terms cannot be coding bases. See [[business-rules]].
- `BR20` and `BR21`: deprecated or dismissed terms are invalid. See [[business-rules]].
- `BR29`, `BR30`, and `BR31`: syntax, facet-category, and descriptor-membership checks. See [[business-rules]].

<!-- Source: docs/VALIDATION_RULES_SUMMARY.md Quick Reference Table; BUSINESS-RULES.md Validation Examples -->
## Worked Examples

- Before: `A0B9Z`. After: valid base-only code. A facet is not required when the base term already fits. (Business Rules Validation Examples)
- Before: `A000J#F01.A0F6E`. After: invalid, `BR03`. Composite terms cannot use `F01 source`. (Business Rules `BR03`)
- Before: `A0B9Z#F99.A07JS`. After: invalid, `BR30`. `F99` is not a valid facet category. (Business Rules `BR30`)
