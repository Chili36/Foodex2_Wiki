---
title: "Ingredient Facets"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf"
related:
  - "[[facet-coding-rules]]"
  - "[[base-term-selection]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-04-08"
---

# Ingredient Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p19-20, p45, p56; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p5-6 -->
## Core Rule

- `F04 Ingredient` is the origin facet for composite foods. Use it to name the characterising ingredient or ingredients that distinguish one composite product from another. The composite-vs-derivative choice still comes first in [[base-term-selection]]. (EFSA guidance p19-20, p56; Training p5)
- It is not a full recipe field. Only one or a few ingredient descriptors are expected, not every component. Recipes belong in an external database if needed, and the same "few facets, high signal" rule is summarized in [[facet-coding-rules]]. (EFSA guidance p56)
- When the ingredient is used mainly for flavour identity, code it as the raw commodity term for consistency. (EFSA guidance p56)
- On derivative base terms, use `F04` for minor added ingredients that characterise or flavour the product, not for the constitutive source of the derivative itself. Ask: was the food obtained from that commodity, or was the commodity added later? This is the same origin-chain distinction described in [[implicit-vs-explicit-facets]] and constrained in [[term-type-facet-constraints]]. (EFSA guidance p19-20, p56)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p45, p49-50, p56; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p6 -->
## Common Combinations

| Situation | Base term | Added facets |
| --- | --- | --- |
| Composite dish | Composite non-hierarchy term | One or a few `F04` characterising ingredients |
| Same-nature mix | Generic raw/derivative term | Multiple `F27`, not `F04` |
| Same-nature mix plus minor foreign components | Generic raw/derivative term | Multiple `F27` plus minor `F04` |
| Balanced mixed natures | Composite base term | Multiple `F04` ingredients |

- `F04` can also be used outside composites for minor ingredients such as flavourings or coatings on an otherwise raw or derivative product. In those cases `F27` still answers what the derivative was obtained from, while `F04` records what was added to characterise it. Use [[implicit-vs-explicit-facets]] to keep that distinction straight. (EFSA guidance p56)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p50, p56 -->
## Worked Examples

- Before: `asparagus risotto`. After: `A041F#F04.A00RT`. A composite base term plus one characterising ingredient. (EFSA guidance p56)
- Before: `mixed leaf salad` with small amounts of carrots and sunflower seeds. After: `A00KR#F04.A00QH$F04.A015L$F27.A00KV$F27.A00LN$F27.A00LB$F27.A00LG`. Same-nature leafy components use `F27`; minor foreign components use `F04`. (EFSA guidance p50)
- Before: `candied citrus peel, chocolate-coated`. After: `A01PS#F04.A034G$F27.A01QE$F28.A07HP`. `F04` records the minor ingredient `chocolate`; `F27` keeps the citrus-peel source commodity. (EFSA guidance p56)

## Relevant Policy

- [[policy-contract]] `C07` is the main policy hook for this page: composites use `F04` for characterising ingredients, while derivatives use `F27` for constitutive source and may use `F04` only for later-added minor ingredients.
- [[policy-contract]] `R-ORIGIN-001` and `R-ORIGIN-002` keep derivative source logic and composite ingredient logic separate.
- [[policy-contract]] `C08` still applies: add ingredient facets only when they materially improve the description.

## Relevant Business Rules

- `BR03` and `BR04`: composites cannot use `F01` or `F27`. See [[business-rules]].
- `BR12`: `F04` on raw or derivative terms is limited to minor added ingredients. See [[business-rules]].
