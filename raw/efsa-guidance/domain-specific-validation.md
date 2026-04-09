---
title: "Domain-Specific Validation"
sources:
  - "docs/DOMAIN_SPECIFIC_RULES.md"
  - "docs/CONTEXT_SPECIFIC_RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
related:
  - "[[business-rules]]"
  - "[[chemical-monitoring-foodex2]]"
  - "[[facet-coding-rules]]"
  - "[[validation-rules]]"
last_updated: "2026-04-05"
---

# Domain-Specific Validation

<!-- Source: docs/DOMAIN_SPECIFIC_RULES.md VMPR Domain, Food Additives Domain, Contaminants Domain; BUSINESS-RULES-COMPACT.json domainSpecificRules -->
## These Rules Are Contextual

- These checks are not universal FoodEx2 syntax rules. They activate only when the reporting domain or analysis context is known. (Domain Specific Rules; Compact JSON)
- They matter most for VMPR, additives, acrylamide, and non-food animal matrices. See [[chemical-monitoring-foodex2]]. (Domain Specific Rules)

<!-- Source: docs/DOMAIN_SPECIFIC_RULES.md Implementation Matrix; docs/CONTEXT_SPECIFIC_RULES.md -->
## Common Mandatory Or Recommended Facets

| Context | Rule |
| --- | --- |
| VMPR standard animal products | `F01` and `F02` mandatory |
| VMPR processed or derivative products | explicit `F01` mandatory |
| Base term `A0C60` non-food animal matrices | `F01` and `F02` mandatory |
| VMPR Plan 3 processed imports | one `F33` mandatory |
| Food additives monitoring | `F33` mandatory, `F03` highly recommended |
| Acrylamide monitoring (paramCode `RF-00000410-ORG`) | `F33` mandatory per CHEMMON12, even if the base term already carries an implicit `F33`. Legal basis: Commission Regulation (EU) 2017/2158 and Recommendation (EU) 2019/1888 |
| Furans or acrylamide heat-treatment reporting | `F17` should be present |
| Bisphenol or phthalates analysis | `F19` packaging should be present |
| Fat-weight expression | `F07` should be present |
| Infant products | `F23` target-consumer recommended |

<!-- Source: docs/DOMAIN_SPECIFIC_RULES.md VMPR Non-food, VMPR Plan 3, Food Additives Domain; docs/CONTEXT_SPECIFIC_RULES.md F01-NONFOOD, F02-NONFOOD, F33-ADDITIVES -->
## Worked Examples

- Before: `A0C60#F02.A0C63` in VMPR non-food context. After: incomplete; add explicit `F01` because `A0C60` requires both `F01` and `F02`. (Domain Specific Rules; Context Specific Rules)
- Before: processed VMPR sample with no explicit `F01`. After: invalid in that domain, even if the animal source feels inferable. (Domain Specific Rules VMPR-RPC)
- Before: food additive sample with no `F33`. After: invalid for additives monitoring; the legislative category is mandatory. (Domain Specific Rules Additives)
- Before: acrylamide result on french fries (`A0BYV`) with no `F33`. After: `A0BYV#F33.A169H`. CHEMMON12 requires the acrylamide legislative class even though `A0BYV` may carry an implicit `F33`. (ChemMon 2026; CHEMMON12)

## Relevant Business Rules

- `BR14` and `BR15`: context-specific validation paths such as ICT / DCF. See [[business-rules]].
- Domain overlays here should still be read alongside the core `BRxx` validator rules. Use [[business-rules]] as the canonical rule index when a domain case activates validation constraints.
