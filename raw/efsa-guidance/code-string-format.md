---
title: "FoodEx2 Code String Format"
select_when: >-
  The case involves assembling or checking the final code string itself: the
  five-character base term, the introducing and separating punctuation, the
  facet-type-and-descriptor segments, their ordering, spacing, and length
  limits that make a composed code syntactically well formed.
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "FoodEx2 codification guidance_2025_12_v3.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-06-12"
---

# Code String Format

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p39-40 -->
## Syntax

```text
<base-term-code>[#Fxx.<descriptor-code>[$Fyy.<descriptor-code>]...]
```

- Every FoodEx2 term code is a unique five-character alphanumeric identifier such as `A032J`. The code itself carries no human-readable meaning. (EFSA guidance p39)
- The base term is mandatory. A base-term-only code is valid; a facet-only code is not. (EFSA guidance p40)
- `#` starts the facet section. `$` separates facet descriptors. There is no trailing `$`. (EFSA guidance p40)
- A facet is written as `Fxx.` plus a five-character descriptor code, for example `F04.A032J`. (EFSA guidance p39-40)
- Spaces are not allowed. Only one FoodEx2 code should be stored in the field. (EFSA guidance p40; ANSES guidance p24)
- Facet order is not fixed by the string grammar, but EFSA/ANSES guidance recommends increasing alphanumeric order by facet header for consistent automated handling. (EFSA guidance p40; ANSES guidance p24)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p39-40 -->
## Worked Examples

- Before: `orange nectar`. After: `A03BG`. Valid because the base term stands alone. (EFSA guidance p40)
- Before: `orange nectar, calcium-fortified, sugar free, organic`. After: `A03BG#F09.A0EXH$F10.A077L$F21.A07SE`. `A03BG` is the base term; each facet segment starts with `Fxx.` and is separated by `$`. (EFSA guidance p40)
- Before: `candied citrus peel, chocolate-coated`. After: `A01PS#F04.A034G$F27.A01QE$F28.A07HP`. This shows a base term plus three distinct facet descriptors. (EFSA guidance p56)

## Relevant Policy

- [[policy-contract]] `R-SYNTAX-001` and `R-LENGTH-001` govern this page directly: final codes must use the canonical `base#facetType.code($facetType2.code2...)` syntax and stay within the SSD2 length limit.
- [[policy-contract]] Decision Procedure step 5 is where this page applies. Syntax is checked after the coding choice has been made but before the result is accepted as complete.

## Relevant Business Rules

- `BR29`: code structure must be valid. See [[business-rules]].
- `BR30`: facet category must exist. See [[business-rules]].
- `BR31`: descriptor must belong to the chosen facet hierarchy. See [[business-rules]].
