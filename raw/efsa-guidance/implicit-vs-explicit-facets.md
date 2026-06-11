---
title: "Implicit vs Explicit Facets"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "FoodEx2 codification guidance_2025_12_v3.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[facet-coding-rules]]"
  - "[[base-term-selection]]"
last_updated: "2026-06-12"
---

# Implicit vs Explicit Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p19-21, p39-40 -->
## Default Logic

- Detailed FoodEx2 base terms already inherit key facets. Do not report implicit facets in datasets; they can be recovered later. (EFSA guidance p39-40)
- Implicit facets are still useful evidence: they identify the part, origin, or process chain already carried by the base term and show which facet family can legitimately be narrowed when the base is too generic. (ANSES guidance p36, p39-41)
- The building order is `part-nature -> source/source-commodities/ingredient -> process`. That order explains why some information is already encoded in the base term itself, and it is the same order followed in [[base-term-selection]] and [[facet-coding-rules]]. (EFSA guidance p20)
- Use the direct origin facet for each food type: raw commodities take `source`, derivatives take `source-commodities`, composites take `ingredient`. Do not jump one level higher in the chain. The term-type-specific limits are summarised in [[term-type-facet-constraints]]. (EFSA guidance p19-20)
- For derivatives, read `F27 Source-commodities` as "from what primary commodity was this derivative obtained?" not "what was added later?" Later-added flavouring, coating, or characterising ingredients belong in `F04 Ingredient`, not `F27`; see [[ingredient-facets]] for the operational rule. (EFSA guidance p19-20, p56)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p54-56; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33 -->
## When To Add An Explicit Facet

| Food type | Usually implicit | Add explicitly when... |
| --- | --- | --- |
| Raw commodity | `F01 Source` | the detailed term is missing or a narrower source is known |
| Derivative | `F27 Source-commodities` | the detailed derivative is missing, a narrower source raw commodity is known, or a same-nature mix must be described; do not use it for later-added characterising ingredients |
| Derivative (broad group) | `F27 Source-commodities` (broad) | the derivative group covers multiple source commodities and the specific one is known; add explicit F27 to narrow, do not fall back to raw + F28 |
| Composite | `F04 Ingredient` | characterising ingredients must be stated or a mixed-nature product is coded as composite |

- In VMPR workflows, explicit facets can override the implicit categorisation if they are reported, so unnecessary explicit repetition is not neutral. See [[vmpr-foodex2]] for the domain-specific overlay. (ChemMon 2026 p33)
- When a derivative base term carries a broad implicit F27, narrow it with an explicit F27 pointing to the specific source commodity. Do not abandon the derivative base term and reconstruct the food from the raw commodity plus F28 — that violates [[policy-contract|AP-001]] and loses the derivative classification. The explicit F27 refines the implicit one; it does not replace the base term.
- If a missing derivative can only be described by a generic derivative base and no suitable `F27` descriptor exists, `F01` may be a narrow tolerated fallback only when it clearly refers to the single source commodity and `F26.A07XE` marks the missing detailed term. Do not generalise this into ordinary `F01` use on derivatives. (ANSES guidance p49-50)
- Exception: for acrylamide monitoring, explicit `F33` is mandatory even if the base term already carries an implicit `F33`. CHEMMON12 enforces this regardless of implicit state; the reporting context is in [[contaminants-foodex2]]. (ChemMon 2026; CHEMMON12)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p54-56 -->
## Worked Examples

- Before: `Adriatic sturgeon meat` when only `sturgeon [meat]` exists. After: `A029E#F01.A0884$F26.A07XE`. `F01` restricts the implicit generic sturgeon source to a more specific child. (EFSA guidance p54-55)
- Before: `glutinous rice flour`. After: `A003F#F26.A07XE$F27.A0F6M`. `F27` restricts the implicit generic rice grain source to a more specific raw commodity. (EFSA guidance p55)
- Before: `risotto with asparagus`. After: `A041F#F04.A00RT`. `F04` states the characterising ingredient of a composite base term. (EFSA guidance p56)

## Relevant Policy

- [[policy-contract]] `C04` and `C08` govern this page directly: do not restate what the base already implies, and add only explicit facets that contribute new information.
- [[policy-contract]] `R-IMPLICIT-001`, `R-FACET-001`, and `AP-001` cover the main failure mode here: do not rebuild a standard derivative from a raw base plus `F28`, and do not keep explicit facets that merely duplicate implicit properties.
- [[policy-contract]] `R-ORIGIN-001` to `R-ORIGIN-003` explain why raw, derivative, and composite terms use different origin-facet families.

## Relevant Business Rules

- `BR05`, `BR06`, and `BR07`: derivative source-chain limits and derivative use of `F01`. See [[business-rules]].
- `BR12`: `F04` on raw or derivative terms remains minor-ingredient only. See [[business-rules]].
- `BR16`: explicit process detail cannot be broader than what is already implicit. See [[business-rules]].
