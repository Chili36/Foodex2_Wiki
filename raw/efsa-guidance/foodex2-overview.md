---
title: "FoodEx2 Overview"
select_when: >-
  The case needs the top-down mental model before coding: what a base term,
  facet, and implicit facet are, how raw commodities, derivatives, and
  composites differ, why hierarchy terms are not reported, and how the
  reporting versus exposure hierarchies shape an unfamiliar first coding
  decision.
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf"
related:
  - "[[base-term-selection]]"
  - "[[facet-coding-rules]]"
  - "[[code-string-format]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-04-05"
---

# FoodEx2 Overview

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p8-10; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p5 -->
## Purpose

- FoodEx2 is a code-based food classification and description system for cross-domain food-safety reporting. It captures both classification and descriptive detail and supports linking occurrence data with food-consumption data for exposure assessment. (EFSA guidance p8-10; Training p5)
- The system is language-independent: the code is stable even when names differ by language or local usage. Scope notes define what each entry covers. (EFSA guidance p8-9, p37-40)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p14-20, 39-41; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p5 -->
## Core Model

| Element | Role |
| --- | --- |
| Base term | Reportable list term that anchors the code; a FoodEx2 code without a base term is invalid. |
| Facet descriptor | Extra detail such as ingredient, process, or production method. |
| Implicit facet | Detail already inherited by the base term and usually not re-entered by the coder. |

- Start from the question "What type of food is this?" and separate foods into raw primary commodities, derivatives, and composite foods. (EFSA guidance p14-15, p40-41; Training p5)
- The internal building logic is `part-nature -> origin facet -> further process`. For raw foods the origin is `source`, for derivatives it is `source-commodities`, and for composites it is `ingredient`. (EFSA guidance p19-20)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p14, 27-35 -->
## Hierarchies

- `Master hierarchy`: full terminology plus implicit-facet inheritance. Technical role only; do not use it for coding. (EFSA guidance p27)
- `Reporting hierarchy`: input-oriented hierarchy for choosing reportable terms with consistent detail. (EFSA guidance p14, p28)
- `Exposure hierarchy`: output-oriented hierarchy for food-consumption and exposure work. Other domain hierarchies support pesticides, biological monitoring, veterinary residues, and botanicals. (EFSA guidance p28-35)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p9-10, 21, 41 -->
## Coding Philosophy

- Code at the most detailed level available. Narrow groups are more reusable across domains than broad aggregates. (EFSA guidance p9-10)
- Do not report hierarchy terms. When source detail is missing, prefer a generic nature-based term over an aggregated hierarchy label. (EFSA guidance p21, p41)
- Add only descriptors not already implicit in the base term. See [[facet-coding-rules]] and [[implicit-vs-explicit-facets]]. (EFSA guidance p9, p20, p39-40)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p40; EFSA Supporting Publications - 2018 -  - Training on FoodEx2.pdf p6 -->
## Worked Examples

- Before: `orange nectar`. After: `A03BG`. A valid FoodEx2 code can be only the base term when no extra detail is needed. (EFSA guidance p40)
- Before: `orange nectar, calcium-fortified, sugar free, organic`. After: `A03BG#F09.A0EXH$F10.A077L$F21.A07SE`. The same base term becomes more specific through added facets. (EFSA guidance p40)
- Before: `quinoa flour` when no dedicated term exists. After: `A04KS#F27.A000R$F26.A07XE`. Use the nearest generic base term plus facets to recover the missing specificity. See [[base-term-selection]]. (Training p6)

## Relevant Policy

- [[policy-contract]] `C01`, `C02`, and `C06` provide the worldview behind this page: determine food type first, evaluate specificity within that type, and avoid hierarchy terms as coding bases.
- [[policy-contract]] `C05` matters here as well: the examples in this overview orient the reader, but the binding decision order still comes from the policy layer and the more specific operational pages.

## Relevant Business Rules

- No single `BRxx` rule governs this overview page.
- When this overview leads to a concrete coding or validation question, continue with [[business-rules]] and the more specific operational pages rather than treating the overview itself as a validator rule source.
