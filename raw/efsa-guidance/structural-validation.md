---
title: "Structural Validation"
select_when: >-
  The case involves the pre-business-rule structural gate: base-term length and
  existence, facet parsing, descriptor-to-category membership, automatic
  removal of implicit facets, and duplicate or single-cardinality detection
  that reject a code before any policy rule runs.
sources:
  - "docs/VBA_STRUCTURAL_RULES_SUMMARY.md"
  - "docs/VALIDATION_RULES_SUMMARY.md"
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
related:
  - "[[code-string-format]]"
  - "[[validation-rules]]"
  - "[[term-type-facet-constraints]]"
last_updated: "2026-04-05"
---

# Structural Validation

<!-- Source: docs/VBA_STRUCTURAL_RULES_SUMMARY.md Code Structure Rules; docs/VALIDATION_RULES_SUMMARY.md Validation Layers -->
## Syntax Checks

- The base term must be exactly 5 alphanumeric characters and must exist in the term database. (VBA Structural Rules Summary)
- Each explicit facet must use `Fxx.YYYYY` format. The first facet is introduced by `#`; later facets use `$`. See [[code-string-format]]. (VBA Structural Rules Summary)
- Structural validation runs before business rules, so malformed codes fail early. (Validation Rules Summary)

<!-- Source: docs/VBA_STRUCTURAL_RULES_SUMMARY.md Facet Descriptor Validation, Facet Category Validation, Implicit Facet Removal, Duplicate Facet Detection; BUSINESS-RULES.md BR25; BUSINESS-RULES-COMPACT.json singleCardinalityFacets -->
## Descriptor And Facet Checks

- Every facet descriptor must exist in the database and belong to the declared facet category. (VBA Structural Rules Summary)
- Facets already implicit in the base term are removed automatically and flagged with a warning, rather than kept in the cleaned code. See [[implicit-vs-explicit-facets]]. (VBA Structural Rules Summary)
- Duplicate facet instances are flagged. Single-cardinality facet groups allow only one explicit value: `F01`, `F02`, `F03`, `F07`, `F11`, `F22`, `F24`, `F26`, `F30`, `F32`, `F34`. (`BR25`; Compact JSON)

<!-- Source: docs/VBA_STRUCTURAL_RULES_SUMMARY.md Processing Order -->
## Validation Order

1. Check base-term format and existence.
2. Parse the facet string.
3. Validate facet format and descriptor existence.
4. Verify descriptor-category membership.
5. Remove implicit facets.
6. Check single-cardinality and duplicates.
7. Hand off the cleaned code to `BR01-BR31`. (VBA Structural Rules Summary)

<!-- Source: docs/VBA_STRUCTURAL_RULES_SUMMARY.md Implicit Facet Removal; BUSINESS-RULES.md BR29, BR31 -->
## Worked Examples

- Before: `A0B9Z#F28.A07JS$F28.A07JS`. After: invalid; duplicate facet instance detected in structural validation. (VBA Structural Rules Summary)
- Before: `A0B9Z#F28`. After: invalid; the facet is incomplete and fails code-structure checks. (`BR29`)
- Before: a code where an explicit facet duplicates one already implicit in the base term. After: the validator removes the redundant facet, keeps the cleaned code, and emits a warning. (VBA Structural Rules Summary)

## Relevant Policy

- [[policy-contract]] Decision Procedure step 5 and `R-SYNTAX-001` / `R-LENGTH-001` govern this page directly: structural validation is the final gate before a composed code is accepted.
- [[policy-contract]] `R-FACET-001` explains why duplicate implicit detail should be removed before the final code is treated as clean.

## Relevant Business Rules

- `BR25`: single-cardinality facet families allow only one value. See [[business-rules]].
- `BR29`, `BR30`, and `BR31`: structure, facet-category validity, and descriptor-membership checks. See [[business-rules]].
