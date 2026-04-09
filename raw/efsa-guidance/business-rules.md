---
title: "Business Rules"
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "foodex2_docs/business_rules.md"
related:
  - "[[validation-rules]]"
  - "[[structural-validation]]"
  - "[[term-type-facet-constraints]]"
  - "[[process-validation-rules]]"
  - "[[domain-specific-validation]]"
last_updated: "2026-04-09"
---

# Business Rules

This page is the canonical wiki target for validator business rules `BR01`-`BR31`.

Use it for two jobs:

- as the central rule index when a page needs to say which `BRxx` rules govern its topic
- as the anchor page for future ingest passes, so operational pages can link to the specific rules that apply

## Severity Model

| Severity | Validation impact | Typical rules |
| --- | --- | --- |
| `ERROR` | Blocking, validation fails | `BR17`, `BR19`, `BR20`, `BR21`, `BR25`, `BR29`, `BR30`, `BR31` |
| `HIGH` | Hard warning, validation fails | `BR01`, `BR03`, `BR04`, `BR05`, `BR06`, `BR07`, `BR08`, `BR13`, `BR14`, `BR16`, `BR24`, `BR26`, `BR27`, `BR28` |
| `LOW` | Soft warning, validation passes | `BR10`, `BR11`, `BR12`, `BR15`, `BR23` |
| `NONE` | Informational only | `BR22` |

`BR02`, `BR09`, and `BR18` are placeholders and are not implemented.

## BR01: Source Commodity Validation for Raw Terms

- Severity: `HIGH`
- Applies to: raw terms with explicit `F27`
- Rule: explicit `F27` must refine the raw commodity chain and be a child of the base or an already implicit `F27`
- Purpose: prevents illogical source specifications on raw foods

## BR03: No Source Facet in Composite Foods

- Severity: `HIGH`
- Applies to: composite terms (`c`, `s`)
- Rule: composites cannot use `F01`; use `F04` instead

## BR04: No Source-Commodities in Composite Foods

- Severity: `HIGH`
- Applies to: composite terms (`c`, `s`)
- Rule: composites cannot use `F27`; use `F04` instead

## BR05: F27 Restrictions for Derivatives

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: explicit `F27` on a derivative must be more specific than the implicit source-commodity chain

## BR06: F01 Source Requires F27

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: `F01` requires a valid `F27` source-commodity chain

## BR07: F01 for Single F27 Only

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: `F01` can only be used when exactly one `F27` is present

## BR08: Non-Reportable Terms Forbidden

- Severity: `HIGH`
- Applies to: all non-reportable terms
- Rule: only reportable terms are valid coding bases

## BR10: Non-Specific Terms Discouraged

- Severity: `LOW`
- Applies to: non-specific terms (`n`)
- Rule: non-specific base terms are discouraged

## BR11: Generic Process Terms Discouraged

- Severity: `LOW`
- Applies to: `F28` process facets
- Rule: generic process labels are discouraged when a more specific process exists

## BR12: Ingredient Facet Restrictions

- Severity: `LOW`
- Applies to: raw (`r`) and derivative (`d`) terms
- Rule: `F04` should be used only for minor ingredients in those term types

## BR13: Physical State Creates Derivatives

- Severity: `HIGH`
- Applies to: raw terms (`r`)
- Rule: `F03` cannot be applied to raw commodities because it creates a derivative

## BR14: ICT/DCF Only Rule

- Severity: `HIGH`
- Applies to: context-specific workflows
- Rule: certain checks are only active in ICT / DCF contexts

## BR15: DCF Only Rule

- Severity: `LOW`
- Applies to: DCF context
- Rule: certain advisory checks are only active in DCF

## BR16: Process Detail Level Check

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: explicit process detail must not be broader than the implicit process

## BR17: Facets as Base Terms Forbidden

- Severity: `ERROR`
- Applies to: facet terms (`f`)
- Rule: facet descriptors cannot be used as base terms

## BR19: Forbidden Processes on Raw Commodities

- Severity: `ERROR`
- Applies to: raw terms (`r`)
- Rule: processes that create derivatives cannot be applied to raw commodities

## BR20: Deprecated Terms

- Severity: `ERROR`
- Applies to: deprecated terms
- Rule: deprecated terms cannot be used

## BR21: Dismissed Terms

- Severity: `ERROR`
- Applies to: dismissed terms
- Rule: dismissed terms cannot be used

## BR22: Success Message

- Severity: `NONE`
- Type: informational
- Rule: confirmation that the base term was successfully added

## BR23: Hierarchy Terms Discouraged

- Severity: `LOW`
- Applies to: hierarchy terms in the exposure hierarchy
- Rule: hierarchy terms as base terms are discouraged

## BR24: Non-Exposure Hierarchy Warning

- Severity: `HIGH`
- Applies to: hierarchy terms outside the exposure hierarchy
- Rule: those hierarchy terms should not be used as coding bases

## BR25: Single Cardinality Enforcement

- Severity: `ERROR`
- Applies to: single-cardinality facet families
- Rule: only one explicit value is allowed for `F01`, `F02`, `F03`, `F07`, `F11`, `F22`, `F24`, `F26`, `F30`, `F32`, `F34`

## BR26: Mutually Exclusive Processes

- Severity: `HIGH`
- Applies to: derivatives with explicit `F28`
- Rule: processes in the same ordinal group cannot be combined

## BR27: Decimal Ordcode Process Conflicts

- Severity: `HIGH`
- Applies to: derivative terms (`d`)
- Rule: decimal ordcodes in the same integer family conflict and represent alternative derivative paths

## BR28: Reconstitution Restrictions

- Severity: `HIGH`
- Applies to: dehydrated, powdered, and concentrated products
- Rule: reconstitution or dilution should not be added; use the reconstituted product instead

## BR29: Code Structure Validation

- Severity: `ERROR`
- Applies to: all codes
- Rule: the code must follow valid FoodEx2 syntax

## BR30: Invalid Facet Category

- Severity: `ERROR`
- Applies to: all facet codes
- Rule: facet category must exist

## BR31: Facet Not in Category Hierarchy

- Severity: `ERROR`
- Applies to: all facet descriptors
- Rule: the descriptor must belong to its facet category hierarchy

## How To Use This Page During Ingest

- For every operational page, ask which `BRxx` rules actually govern the topic.
- Add a short `Relevant Business Rules` section to that page.
- Link each referenced rule back to this page.
- Do not add rules just because they are nearby; link the rules that materially constrain the page's decisions.
