---
title: "Business Rules"
select_when: >-
  The case needs the authoritative meaning, scope, and severity of a specific
  numbered business rule: whether a construction is a blocking error, a hard or
  soft warning, plus validator data-status caveats such as the disintegration
  physical-state, forbidden-process, and mutually-exclusive-process boundaries.
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
last_updated: "2026-06-07"
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

## Validator Data Status

- Operational provenance: this status reflects the sibling validator PR stream for the MTX `17.1` import, BR13 ICT parity, BR19 extension layer, and BR26 audit. Treat these as validator-maintenance facts, not new EFSA ontology authority.
- The sibling validator's MTX `17.1` update stream imports MTX `17.1` on 2026-06-06. The catalogue status is `PUBLISHED MINOR`, with 31,690 terms and last EFSA update date 2026-04-28. In that import, 410 terms are tagged `17.1`, with a net increase of 10 unique `termCode` values compared with MTX `17.0`.
- The BR19 forbidden-process source file `BR_Data.csv` is older than the MTX catalogue. It was last updated upstream on 2020-05-20, so some root groups added or reorganised after that date are not covered by the official BR19 table.
- The sibling validator can load an additive `BR_Data.extension.csv` after the official `BR_Data.csv`. Extension rows are labelled `BR19+` in warnings, carry rationale/date fields, and can be disabled with `STRICT_ICT_PARITY=1` when strict stock-ICT comparison is required.
- Treat extension rows as validator evidence for clear data-freshness gaps, not as new FoodEx2 ontology. The long-term fix is upstream rule-data refresh; the extension layer is a transparent local bridge.

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
- Rule: `BR13` fires on raw commodities only when explicit `F03` is one of the seven ICT disintegration descriptors below. It does not mean that every `F03` physical-state descriptor is forbidden on raw commodities.
- Forbidden `F03` descriptors: `A06JD` powder, `A06JE` coarse paste/minced, `A06JF` paste, `A06JG` puree-type, `A07Y2` fine powder, `A07Y3` coarse powder, `A07Y4` fine paste.
- Boundary: non-disintegration physical states such as `A0C2M` solid or `A0C3M` liquid can be valid on a raw commodity if all other rules pass.
- Operational reading for DMT/LLM consumers: "powder/paste/puree-style disintegration cannot be added to a raw base" is correct; "no `F03` on raw" is too broad.

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
- Data-source note: official BR19 coverage comes from `BR_Data.csv`, which is frozen upstream at 2020-05-20. Because MTX is now at `17.1`, some clear-pattern root groups can be absent from the official BR19 table.
- Local-extension note: the sibling validator can add transparent `BR19+` rows from `data/BR_Data.extension.csv`. The extension uses the same five official columns plus `RATIONALE` and `ADDED`; official rows take precedence when the same root/process pair exists.
- Workflow impact: stock ICT can be silent where local validation flags a derivative-creating process on a raw commodity. This is expected when the local warning is `BR19+`, and can be disabled with `STRICT_ICT_PARITY=1` for strict stock-ICT parity checks.

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
- Known divergence: in the observed stock ICT source, the `mutuallyExclusiveCheck` call appears to be inactive, so BR26 is effectively silent. The sibling validator is also effectively silent for BR26 at present because its process ordinal lookup resolves to `0` for the derivative cases where BR26 would apply. The outcome matches stock ICT silence, but the implementation cause differs.
- Practical reading: do not rely on BR26 firing as evidence that same-ordinal process combinations are semantically good. Keep the process-composition guidance in [[process-validation-rules]], and treat a proper BR26 implementation as deferred validator work.

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

## Relevant Policy

- [[policy-contract]] is not an independent rulebook. It is the solver-facing execution order distilled from this page plus the ordinary guidance pages.
- When a policy item cites a `BRxx` rule from this page, treat the `BRxx` rule as the controlling authority and the policy item as an application-order shortcut for the solver.

## Relevant Business Rules

- This page is the canonical wiki index for `BR01-BR31`.
- Other pages should backlink only the `BRxx` rules that materially constrain their topic; do not treat every page as governed by every business rule.
