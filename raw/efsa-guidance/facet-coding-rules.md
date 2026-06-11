---
title: "Facet Coding Rules"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "FoodEx2 codification guidance_2025_12_v3.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[process-facets]]"
  - "[[ingredient-facets]]"
  - "[[packaging-facets]]"
last_updated: "2026-06-12"
---

# Facet Coding Rules

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p35-36, p39-40, p46-47; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33 -->
## General Rule

- Add facets only when they refine the chosen base term in a way that matters for coding or reporting. If the base term already carries the detail implicitly, do not repeat it explicitly; the default logic is spelled out in [[implicit-vs-explicit-facets]]. (EFSA guidance p39-40; ChemMon 2026 p33)
- In practice, only a few facets are needed. The number of possible facets is not the target; focus on descriptors that define a meaningful subgroup or retain source information that would otherwise be lost. (EFSA guidance p46-47; ANSES guidance p37-38)
- `F13` to `F16` are largely deprecated; use `F28 process` instead, following [[process-facets]]. (EFSA guidance p46-47)
- Use implicit facets as evidence. They should usually not be repeated, but they can show which facet family should be used to narrow a generic or insufficient base term. (ANSES guidance p36, p39-41)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p35-36, p39-40, p46-47, p56; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33-36, p54-55 -->
## Facet Category Reference

Use this table to map an explicit descriptor candidate to the correct `Fxx` family. It is a category guide, not a descriptor catalog; exact descriptor membership should still come from the candidate or validator data.

| Facet | Meaning | Use |
| --- | --- | --- |
| `F01` | Source | Biological source where explicit source is permitted or required; do not add it merely to restate a raw base commodity. |
| `F02` | Part-nature | Part or sample-matrix nature, especially when a generic matrix needs an explicit part. |
| `F03` | Physical state | Physical form or state. On raw commodities, BR13 blocks only disintegration-family physical states such as powder, paste, and puree; non-disintegration states such as solid can be valid when otherwise legal. |
| `F04` | Ingredient | Characterising recipe ingredient for composites, or a minor later-added ingredient on otherwise raw or derivative foods. |
| `F06` | Surrounding medium | Packing or surrounding medium such as liquid, brine, oil, or sauce when it matters separately from packaging. |
| `F07` | Fat content | Fat-content expression when the reporting context or result basis needs it. |
| `F09` | Fortification component | Added enrichment or fortification component, such as calcium in a fortified product. |
| `F10` | Qualitative information | Qualitative descriptors such as light, sugar-free, lactose-free, or similar non-process attributes. |
| `F11` | Alcohol content | Alcohol-content expression for alcoholic beverages when the exact or labelled alcohol percentage matters. |
| `F17` | Cooking extent | Heat-treatment or cooking-extent detail when a domain rule asks for it, for example furans or acrylamide reporting. |
| `F18` | Packaging format | Container or presentation format such as jar, bottle, can, box, or wrapper. |
| `F19` | Packaging material | Contact material such as glass, plastic, paper, or metal. |
| `F20` | Part consumed or analysed | Analysed or consumed part detail when downstream classification needs it. |
| `F21` | Production method or growing condition | Production or husbandry method such as organic, wild, aquaculture, indoor, greenhouse, or under-glass growing. |
| `F23` | Target consumer | Intended consumer group, including infant products and animal feed target categories. |
| `F24-F25` | Microbiology-specific facets | Specialist microbiological reporting descriptors; use only in microbiology contexts. |
| `F26` | Other or missing-detail marker | Add when the exact detailed term is missing and the generic base or origin facet needs an `other` marker. |
| `F27` | Source commodity | Constitutive source commodity for derivatives or same-nature raw/derivative mixtures. |
| `F28` | Process | Treatment or processing detail that is not already implicit in the selected base term. |
| `F29-F32` | Animal-domain facets | Specialist animal-domain descriptors; use only when the reporting domain activates them. |
| `F33` | Legislative class | Legislation-oriented reporting class, mainly in chemical monitoring, VMPR, additives, and flavourings contexts. |
| `F34` | Host sampled | Host-sampled descriptor introduced for relevant host/vector reporting contexts. |

- If a candidate is a facet descriptor, it still cannot be the base term. First choose the base term, then attach the descriptor under the correct `Fxx` family only if it adds non-implicit information.
- A descriptor such as `Indoor/under glass growing condition` belongs under `F21` because it describes production or growing method. In a raw commodity case such as greenhouse cherry tomatoes, the base remains the raw commodity and the greenhouse detail is an optional explicit `F21` when that detail matters.
- A descriptor such as `Powder`, `Fine powder`, `Coarse powder`, `Paste`, `Fine paste`, `coarse paste/minced`, or `Puree-type` belongs to the BR13 disintegration boundary when attached as `F03` to a raw commodity. Do not generalise that into a ban on every `F03` descriptor for raw commodities; verify the actual descriptor and rule result.
- Numeric content facets such as `F07` fat content and `F11` alcohol content are single-cardinality. When the source gives a range, do not attach both endpoints; choose the reporting-context convention for reducing the range to one descriptor or leave the range in text if no exact FoodEx2 descriptor is defensible. (ANSES guidance p58)
- When similar information is available as both a process and a qualitative product claim, prefer the descriptor that matches the source meaning. For example, a labelled low/reduced-lactose product is normally better expressed as qualitative information than as a manufacturing-process fact. (ANSES guidance p45)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p35-36, p46-47 -->
## High-Value Facets

| Facet | Use |
| --- | --- |
| `F01` / `F27` / `F04` | Origin facets for raw commodities, derivatives, and composites respectively. |
| `F28` | Important treatment not already implicit in the base term. |
| `F06` | Surrounding medium for canned or packed foods. |
| `F10` | Qualitative info such as light, sugar free, lactose free. |
| `F21` | Production method such as organic, aquaculture, wild. |
| `F26` | Required when coding from a generic term because the exact detailed term is missing. |

- Specialist facets are domain-bound: `F24-F25` for microbiology, `F29-F32` for animal-domain coding, `F33` for legislation-oriented reporting. When those domain overlays matter, continue with [[chemical-monitoring-foodex2]], the relevant reporting-domain page, and [[domain-specific-validation]]. (EFSA guidance p35-36)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p40, p47-48; EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf p33-36 -->
## Worked Examples

- Before: `orange nectar`. After: `A03BG`. No extra facets are needed when the base term already captures the intended level of detail. (EFSA guidance p40)
- Before: `orange nectar, calcium-fortified, sugar free, organic`. After: `A03BG#F09.A0EXH$F10.A077L$F21.A07SE`. Add only the extra descriptors that are not implicit in `A03BG`. (EFSA guidance p40)
- Before: `cow hair sample` in VMPR. After: `A0C60#F02.A0ESP$F01.A057E`. In this special domain case, explicit `F02` and `F01` are required because the base term is intentionally generic. (ChemMon 2026 p36)

## Relevant Policy

- [[policy-contract]] `C07` and `C08` are the main policy layer for this page: pick the facet family that matches the chosen food type and add only information that is not already implicit in the base term.
- [[policy-contract]] `R-FACET-001` and `R-DESC-001` explain the main coding discipline here: remove redundant explicit detail, but keep descriptive facets such as `F10` and `F21` when they add real information.

## Relevant Business Rules

- `BR12`: `F04` on raw or derivative terms is limited to minor added ingredients. See [[business-rules]].
- `BR25`: single-cardinality facet families can only appear once. See [[business-rules]].
- `BR30` and `BR31`: every explicit facet must use a valid category and a descriptor that belongs to that category. See [[business-rules]].
