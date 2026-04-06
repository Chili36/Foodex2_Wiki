---
title: "FoodEx2 Code String Format"
sources:
  - "EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-04-05"
---

# Code String Format

<!-- Source: EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf p39-40 -->
## Syntax

```text
<base-term-code>[#Fxx.<descriptor-code>[$Fyy.<descriptor-code>]...]
```

- Every FoodEx2 term code is a unique five-character alphanumeric identifier such as `A032J`. The code itself carries no human-readable meaning. (EFSA guidance p39)
- The base term is mandatory. A base-term-only code is valid; a facet-only code is not. (EFSA guidance p40)
- `#` starts the facet section. `$` separates facet descriptors. There is no trailing `$`. (EFSA guidance p40)
- A facet is written as `Fxx.` plus a five-character descriptor code, for example `F04.A032J`. (EFSA guidance p39-40)
- Spaces are not allowed. Only one FoodEx2 code should be stored in the field. (EFSA guidance p40)
- Facet order is not fixed, but EFSA recommends increasing alphabetical order by facet header. (EFSA guidance p40)

<!-- Source: EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf p39-40 -->
## Worked Examples

- Before: `orange nectar`. After: `A03BG`. Valid because the base term stands alone. (EFSA guidance p40)
- Before: `orange nectar, calcium-fortified, sugar free, organic`. After: `A03BG#F09.A0EXH$F10.A077L$F21.A07SE`. `A03BG` is the base term; each facet segment starts with `Fxx.` and is separated by `$`. (EFSA guidance p40)
- Before: `candied citrus peel, chocolate-coated`. After: `A01PS#F04.A034G$F27.A01QE$F28.A07HP`. This shows a base term plus three distinct facet descriptors. (EFSA guidance p56)
