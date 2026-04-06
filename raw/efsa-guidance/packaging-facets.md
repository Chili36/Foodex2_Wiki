---
title: "Packaging Facets"
sources:
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
  - "EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance  2026 data collection.pdf"
related:
  - "[[facet-coding-rules]]"
  - "[[code-string-format]]"
  - "[[process-facets]]"
  - "[[chemical-monitoring-foodex2]]"
last_updated: "2026-04-05"
---

# Packaging Facets

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p46-47 -->
## Core Rule

- `F18 Packaging-format` and `F19 Packaging-material` are general FoodEx2 facets. EFSA treats them as important when the packaging matters for the product or the data-collection purpose. (EFSA guidance p46-47)
- In practice, add them case by case, not by default for every food. The 2015 guide says packaging facets are driven by the purpose of the data collection. (EFSA guidance p46-47)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p46-47; EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance  2026 data collection.pdf p54-55 -->
## F18 Vs F19

| Facet | Meaning | Example |
| --- | --- | --- |
| `F18` | Container or wrap format | `jar`, `bottle`, `box` |
| `F19` | Material in contact with the food | `glass`, `polypropylene`, `laminated paper-plastic foil` |

- If the query says `glass jar`, the natural split is `F18 jar` plus `F19 glass`. (ChemMon 2026 p54-55)
- If the query gives only the container shape, add only `F18`; if it gives only the material, add only `F19`. (Inference from ChemMon 2026 p54-55)

<!-- Source: EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p17-18; EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance  2026 data collection.pdf p55 -->
## Packaging Is Not The Same As Process

- `F18` and `F19` describe the marketed package. `F28` describes a treatment or preservation process. See [[process-facets]]. (EFSA guidance p17-18; ChemMon 2026 p55)
- EFSA's top-down examples show that `jarring` can be added as a process descriptor when it is part of the preservation state of the product. (EFSA guidance p17-18)
- Inference: a `jar` alone supports `F18` and maybe `F19`; it does not by itself prove a specific thermal treatment such as `pasteurisation`. The ChemMon examples code packaging and process separately. (Inference from ChemMon 2026 p54-55)

<!-- Source: EFSA Supporting Publications - 2026 - Chemical monitoring reporting guidance  2026 data collection.pdf p54-55; EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p17-18 -->
## Worked Examples

- Before: `pizza taken in a takeaway shop, packed in a laminated pizza box`. After: `A03ZN#F18.A07NL$F19.A07PN`. Packaging alone can be enough when the marketed pack matters. (ChemMon 2026 p54)
- Before: `infant formula based on milk, heated in the microwave inside a plastic feeding bottle`. After: `A03QF#F28.A07HB$F18.A07NM$F19.A16RX`. Process and packaging can coexist, but they are separate descriptors. (ChemMon 2026 p55)
- Before: `pickled cucumbers in a glass jar`. After: start from the pickled-vegetable base term and add the `jarring` process facet; if the marketed pack detail matters, add packaging facets separately. (EFSA guidance p17-18)
