# DMT FoodEx2 Challenge Suite From Nutrients 2024 Paper

Source: `/Users/davidfoster/Downloads/nutrients-16-01065.pdf`

This is a compact challenge set extracted from the broader paper-derived test list. The paper is about FoodEx2 harmonisation of a children’s food-consumption database, not monitoring data. These cases are therefore not blind universal gold standards for monitoring workflows. They are paper-referenced probes for DMT behavior: candidate recall, facet-family placement, final construction, and validator interaction.

Use them to test whether DMT can recover and assemble FoodEx2 building blocks from facet-heavy consumed-food descriptions. Do not use them as evidence for contaminants, pesticides, VMPR, sample-taking, or other reporting-domain overlays.

## Scoring

- `base_recall`: expected base appears in retrieved candidates.
- `facet_recall`: expected facet descriptors appear in retrieved candidates.
- `facet_family`: descriptors are attached to the expected facet family.
- `fact_coverage`: each meaningful source fact is explicit, implicit, unsupported, or deliberately not coded.
- `construction`: final code matches the paper consumption-data example or a validated, explicitly justified alternative.
- `validation`: final code passes the validator, or the failure is explained as a paper-vs-validator/domain-context issue.

## Why These Cases

The earlier smoke test showed that a single natural-language query found 56 of 99 expected base/facet codes, while component queries found 98 of 99. These cases therefore test the core DMT hypothesis:

`source text -> fact deconstruction -> base candidate search + per-fact facet searches -> wiki guidance/context -> classifier -> validator`

They are poor tests for a single-vector-search workflow because many facet descriptors are semantically small compared with the full food phrase.

## Cases

| ID | Input | Main Challenge |
| --- | --- | --- |
| `challenge-fortified-chocolate-rice-cereal` | Popped rice breakfast cereal with chocolate flavour, fortified with vitamins and iron. | Base found by single query, but F04/F09/F10 facets were missed. |
| `challenge-follow-on-formula-fortified-powder` | Milk-based follow-on formula powder fortified with calcium, iron, and vitamin C. | Infant formula base plus nutrient fortification facets. |
| `challenge-ready-to-eat-child-meal-jar-homogenized` | Ready-to-eat meat-based meal for children, homogenized, containing calf meat, chicken meat, and leafy vegetables, packed in a jar. | Product base plus F28 process, F04 ingredients, and F18 packaging. |
| `challenge-spreadable-cheese-low-fat-17-percent` | Processed spreadable cheese, low fat, 17 percent fat. | Qualitative fat descriptor vs exact fat percentage: F10 and F07 must not be confused. |
| `challenge-yoghurt-apricot-skimmed-no-added-sugar-01-fat` | Flavoured cow milk yoghurt, apricot flavour, skimmed, without added sugar, 0.1 percent fat. | Flavour, qualitative descriptors, and exact fat percentage in one code. |
| `challenge-vitamin-d-liquid-supplement` | Vitamin D only supplement in liquid formulation. | Active nutrient as F04 and formulation state as F03. |
| `challenge-meat-imitate-wheat-chickpea-processes` | Meat imitate based on common wheat grain and chickpeas, ground, salted, and preserved with additives. | Multiple source commodities and multiple process facets. |
| `challenge-canned-sweet-corn-without-medium` | Canned sweet corn, drained or without surrounding medium. | Extra fact is F20, not another process or ingredient. |
| `challenge-canned-artichokes-in-olive-oil` | Canned or jarred globe artichokes in olive oil. | Generic processed base plus F27 source and F06 surrounding medium. |
| `challenge-tiramisu-recipe-aggregate` | Tiramisu dessert with sweet plain biscuits, mascarpone, coffee beverage, and cocoa powder. | Recipe aggregation and acceptable-alternative handling. |
| `challenge-cod-breaded-deep-fried` | Codfish, breaded and deep fried. | Consumption-occasion processing and multiple F28 facets. |
| `challenge-ricotta-full-fat-cow-sheep` | Full-fat ricotta made from cow milk and sheep milk. | Multiple F27 source-commodity refinements plus qualitative fat descriptor. |

Machine-readable cases are in `dmt_foodex2_challenge_suite.json`.
