---
title: "Implicit vs Explicit Facets"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[base-term-selection]]"
last_updated: "2026-04-06"
---

# Implicit vs Explicit Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p19-21, p39-40 -->
## Default Logic

- Detailed FoodEx2 base terms already inherit key facets. Do not report implicit facets in datasets; they can be recovered later. (EFSA guidance p39-40)
- The building order is `part-nature -> source/source-commodities/ingredient -> process`. That order explains why some information is already encoded in the base term itself. (EFSA guidance p20)
- Use the direct origin facet for each food type: raw commodities take `source`, derivatives take `source-commodities`, composites take `ingredient`. Do not jump one level higher in the chain. (EFSA guidance p19-20)
- For derivatives, read `F27 Source-commodities` as "from what primary commodity was this derivative obtained?" not "what was added later?" Later-added flavouring, coating, or characterising ingredients belong in `F04 Ingredient`, not `F27`. (EFSA guidance p19-20, p56)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p54-56; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33 -->
## When To Add An Explicit Facet

| Food type | Usually implicit | Add explicitly when... |
| --- | --- | --- |
| Raw commodity | `F01 Source` | the detailed term is missing or a narrower source is known |
| Derivative | `F27 Source-commodities` | the detailed derivative is missing, a narrower source raw commodity is known, or a same-nature mix must be described; do not use it for later-added characterising ingredients |
| Composite | `F04 Ingredient` | characterising ingredients must be stated or a mixed-nature product is coded as composite |

- In VMPR workflows, explicit facets can override the implicit categorisation if they are reported, so unnecessary explicit repetition is not neutral. (ChemMon 2026 p33)
- Exception: for acrylamide monitoring, explicit `F33` is mandatory even if the base term already carries an implicit `F33`. CHEMMON12 enforces this regardless of implicit state. (ChemMon 2026; CHEMMON12)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p54-56 -->
## Worked Examples

- Before: `Adriatic sturgeon meat` when only `sturgeon [meat]` exists. After: `A029E#F01.A0884$F26.A07XE`. `F01` restricts the implicit generic sturgeon source to a more specific child. (EFSA guidance p54-55)
- Before: `glutinous rice flour`. After: `A003F#F26.A07XE$F27.A0F6M`. `F27` restricts the implicit generic rice grain source to a more specific raw commodity. (EFSA guidance p55)
- Before: `risotto with asparagus`. After: `A041F#F04.A00RT`. `F04` states the characterising ingredient of a composite base term. (EFSA guidance p56)
