---
title: "Term Type And Facet Constraints"
sources:
  - "BUSINESS-RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "docs/VALIDATION_RULES_SUMMARY.md"
  - "EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf"
related:
  - "[[base-term-selection]]"
  - "[[business-rules]]"
  - "[[facet-coding-rules]]"
  - "[[validation-rules]]"
  - "[[process-validation-rules]]"
last_updated: "2026-04-08"
---

# Term Type And Facet Constraints

<!-- Source: BUSINESS-RULES-COMPACT.json termTypeRules; docs/VALIDATION_RULES_SUMMARY.md Term Types, Quick Reference Table -->
## Core Matrix

| Term type | Use as base term | Typical explicit facets | Main restrictions |
| --- | --- | --- | --- |
| `r` raw commodity | Yes | `F27`, `F28` | No `F01`, `F03`, `F04`; `F27` must refine the base (`BR01`); some processes are forbidden (`BR19`) |
| `d` derivative | Yes | `F01`, `F27`, `F28`, `F03` | `F01` only with exactly one `F27` (`BR06-BR07`); `F27` must be more specific than implicit (`BR05`) and should describe the constitutive source commodity, not later-added ingredients |
| `c` / `s` composite | Yes | `F04`, `F28` | No `F01` or `F27` (`BR03-BR04`) |
| `h` / `g` hierarchy or group | Avoid | None by default | Discouraged or invalid as reporting bases (`BR23-BR24`) |
| `f` facet term | No | None | Cannot be a base term (`BR17`) |
| `n` non-specific | Avoid | Case-specific | Discouraged because precision is too low (`BR10`) |

<!-- Source: BUSINESS-RULES.md BR01, BR03, BR04, BR05, BR06, BR07, BR12, BR13, BR17, BR23, BR24; EFSA Supporting Publications - 2015 -  - The food classification and description system FoodEx 2  revision 2.pdf p19-20, p56 -->
## Practical Reading

- Raw terms are anchored on the commodity itself. `F03 physical state` is blocked because it creates a derivative (`BR13`), and some `F28` processes are also blocked for the same reason; see [[process-validation-rules]]. (Business Rules `BR01`, `BR13`)
- Derivatives use the source-commodity model. Read `F27` as "from what primary commodity was this derivative obtained?" If `F01 source` is needed, the derivative must already resolve to exactly one `F27`. Later-added flavouring or characterising ingredients belong in `F04`, not `F27`; the origin-chain explanation is in [[implicit-vs-explicit-facets]] and the operational use of `F04` is in [[ingredient-facets]]. (EFSA guidance p19-20, p56; Business Rules `BR05-BR07`)
- Composites use ingredient logic, not source logic. Reach for `F04`, not `F01` or `F27`, after [[base-term-selection]] has already established that the food is composite. (Business Rules `BR03-BR04`, `BR12`)
- Facet terms and most hierarchy/group terms may appear in search results, but they should not win base-term selection. For the blocking and advisory effects of those mistakes, see [[validation-rules]]. (Business Rules `BR17`, `BR23-BR24`)

<!-- Source: BUSINESS-RULES-COMPACT.json validationExamples; BUSINESS-RULES.md BR04, BR13 -->
## Worked Examples

- Before: raw commodity + `F28.A07KQ` freezing. After: valid when the process is allowed for that raw term. (Compact JSON validation examples; `BR19`)
- Before: `A0EZJ#F03.A0BZS`. After: invalid, `BR13`. Raw commodities cannot take `F03 physical state`. (Business Rules `BR13`)
- Before: `A02LS#F27.A0EZJ`. After: invalid, `BR04`. A composite such as pizza must use `F04 ingredient` instead. (Business Rules `BR04`)

## Relevant Business Rules

- `BR01`: raw-term `F27` must refine the source chain. See [[business-rules]].
- `BR03` and `BR04`: composites cannot use `F01` or `F27`. See [[business-rules]].
- `BR05`, `BR06`, and `BR07`: derivative source and `F01` restrictions. See [[business-rules]].
- `BR12`: `F04` on raw or derivative terms is minor-ingredient only. See [[business-rules]].
- `BR13`: `F03` creates derivatives and is not allowed on raw commodities. See [[business-rules]].
- `BR17`, `BR23`, and `BR24`: facet terms and hierarchy terms should not win as base terms. See [[business-rules]].
