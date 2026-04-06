---
title: "Facet Coding Rules"
sources:
  - "EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf"
  - "EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance 2026 data collection.pdf"
related:
  - "[[foodex2-overview]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[process-facets]]"
  - "[[ingredient-facets]]"
last_updated: "2026-04-05"
---

# Facet Coding Rules

<!-- Source: EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf p35-36, p39-40, p46-47; EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance 2026 data collection.pdf p33 -->
## General Rule

- Add facets only when they refine the chosen base term in a way that matters for coding or reporting. If the base term already carries the detail implicitly, do not repeat it explicitly. (EFSA guidance p39-40; ChemMon 2026 p33)
- In practice, only a few facets are needed. Focus on the treatments or descriptors that make the difference. (EFSA guidance p46-47)
- `F13` to `F16` are largely deprecated; use `F28 process` instead. (EFSA guidance p46-47)

<!-- Source: EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf p35-36, p46-47 -->
## High-Value Facets

| Facet | Use |
| --- | --- |
| `F01` / `F27` / `F04` | Origin facets for raw commodities, derivatives, and composites respectively. |
| `F28` | Important treatment not already implicit in the base term. |
| `F06` | Surrounding medium for canned or packed foods. |
| `F10` | Qualitative info such as light, sugar free, lactose free. |
| `F21` | Production method such as organic, aquaculture, wild. |
| `F26` | Required when coding from a generic term because the exact detailed term is missing. |

- Specialist facets are domain-bound: `F24-F25` for microbiology, `F29-F32` for animal-domain coding, `F33` for legislation-oriented reporting. (EFSA guidance p35-36)

<!-- Source: EFSA Supporting Publications - 2015 - The food classification and description system FoodEx 2 revision 2.pdf p40, p47-48; EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance 2026 data collection.pdf p33-36 -->
## Worked Examples

- Before: `orange nectar`. After: `A03BG`. No extra facets are needed when the base term already captures the intended level of detail. (EFSA guidance p40)
- Before: `orange nectar, calcium-fortified, sugar free, organic`. After: `A03BG#F09.A0EXH$F10.A077L$F21.A07SE`. Add only the extra descriptors that are not implicit in `A03BG`. (EFSA guidance p40)
- Before: `cow hair sample` in VMPR. After: `A0C60#F02.A0ESP$F01.A057E`. In this special domain case, explicit `F02` and `F01` are required because the base term is intentionally generic. (ChemMon 2026 p36)
