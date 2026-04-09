---
title: "Base Term Selection Rules"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[ingredient-facets]]"
  - "[[process-facets]]"
last_updated: "2026-04-08"
---

# Base Term Selection

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p41-46; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p5-6 -->
## Start With Food Type

- First ask: `What type of food is this?` Choose among raw commodity, derivative, or composite. The base-term decision is the main coding decision; often the base term alone is enough. For the top-down mental model behind this step, start with [[foodex2-overview]]. (EFSA guidance p42; Training p5)
- Never start from a hierarchy term if a reportable non-hierarchy term exists. If poor source data makes that unavoidable, prefer an exposure-hierarchy term. (EFSA guidance p41, p47)
- Know the reporting or exposure hierarchy before coding. Stopping at the first search hit can lead to the wrong branch. (EFSA guidance p42)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p14-20, p42-46, p58 -->
## Choose The Base-Term Class

- Use a raw-commodity base term for primary plant or animal products. Add only treatments that do not create a new nature; if the treatment question becomes ambiguous, read this together with [[process-facets]] and [[process-validation-rules]]. (EFSA guidance p42-44)
- Use a derivative base term when a nature-changing process already defines a standard group. The process list here is illustrative, not exhaustive: this includes cases such as milling, drying, curing, fermentation, pickling/marinating, canning/jarring or smoking whenever FoodEx2 already has the processed group. Do not rebuild these from a raw term plus `F28` if the derivative group exists. The origin chain that follows from that choice is explained in [[implicit-vs-explicit-facets]]. (EFSA guidance p15-17, p44, p58)
- Use a composite base term for foods made by combining ingredients in a recipe. For same-nature mixtures, stay on a generic raw/derivative base term and add multiple `F27`. For balanced mixed natures, move to a composite base term, then describe the characterising recipe components with [[ingredient-facets]]. (EFSA guidance p45, p49-50; Training p6)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p18-19, p47-49 -->
## Tie-Break Rules

- If several preservation processes apply, choose the processed base term top-down: puree/textured, then marinated/pickled/fermented, then in vinegar/brine, in alcohol, salted, candied/sugar-preserved, dried, canned/jarred, smoked. Read this as a precedence rule among processed-base options, not as permission to fall back to a raw base just because the more specific raw commodity exists. (EFSA guidance p18)
- If a composite has no clear dominant ingredient, use this priority: meat, fish, cheese/dairy, egg, legume, potato, cereal, fruit, vegetable. (EFSA guidance p18-19)
- If the exact term is missing, choose the nearest generic non-hierarchy base term, add the correct origin facet, and add `F26.A07XE` (`other`). If even the origin term is missing, keep the generic base term and record the detail in text. Use [[implicit-vs-explicit-facets]] and [[term-type-facet-constraints]] to pick the correct origin facet for the chosen term type. (EFSA guidance p47-49)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p48-50; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p6 -->
## Worked Examples

- Before: `kangaroo fresh fat tissue`. After: `A0F3G#F01.A0F2G$F26.A07XE`. Generic raw base term plus `F01` because the detailed commodity is missing but the source exists. (EFSA guidance p48)
- Before: `quinoa flour`. After: `A04KS#F26.A07XE$F27.A000R`. Generic derivative base term plus `F27` because the detailed derivative is missing but the source raw commodity exists. (EFSA guidance p48; Training p6)
- Before: `mixed vegetable salad` with balanced different-nature ingredients. After: `A042D#F04.A00QH$F04.A015L$F04.A00KV$F04.A00LN$F04.A00LB$F04.A00LG`. Because no single nature dominates, the starting point becomes a composite salad term. (EFSA guidance p50)

## Relevant Policy

- [[policy-contract]] `C01`, `C02`, `C03`, `C06`, and `C09` govern this page directly: determine food type first, read scope notes, prefer reportable non-hierarchy terms, and apply specificity only within the selected food type.
- [[policy-contract]] Decision Procedure steps 1 to 3 are the operative order here: classify the food, compare candidates within that type, then resolve origin and tie-break questions before composing facets.

## Relevant Business Rules

- `BR08`: the selected base term must be reportable. See [[business-rules]].
- `BR10`: non-specific base terms are only weak fallbacks when a more precise reportable term exists. See [[business-rules]].
- `BR19`: derivative-creating processes on raw bases are not an acceptable fallback when the derivative group exists. See [[business-rules]].
- `BR23` and `BR24`: hierarchy terms are discouraged or invalid as coding bases, depending on hierarchy/reporting status. See [[business-rules]].
