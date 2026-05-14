---
title: "Domain-Specific Validation"
sources:
  - "docs/DOMAIN_SPECIFIC_RULES.md"
  - "docs/CONTEXT_SPECIFIC_RULES.md"
  - "BUSINESS-RULES-COMPACT.json"
  - "Guidance VMPR mapping to legislative products.pdf"
related:
  - "[[business-rules]]"
  - "[[chemical-monitoring-foodex2]]"
  - "[[pesticides-foodex2]]"
  - "[[contaminants-foodex2]]"
  - "[[vmpr-foodex2]]"
  - "[[additives-flavourings-foodex2]]"
  - "[[facet-coding-rules]]"
  - "[[validation-rules]]"
  - "[[vmpr-legislative-mapping]]"
last_updated: "2026-05-14"
---

# Domain-Specific Validation

<!-- Source: docs/DOMAIN_SPECIFIC_RULES.md VMPR Domain, Food Additives Domain, Contaminants Domain; BUSINESS-RULES-COMPACT.json domainSpecificRules -->
## These Rules Are Contextual

- These checks are not universal FoodEx2 syntax rules. They activate only when the reporting domain or analysis context is known. (Domain Specific Rules; Compact JSON)
- They matter most for VMPR, additives/flavourings, contaminants substance rules such as acrylamide, and non-food animal matrices. Start from [[chemical-monitoring-foodex2]], then use the relevant domain page. (Domain Specific Rules)
- If the context is all-domain FoodEx2 and no domain-filtered candidate set is active, do not apply these validation overlays by default.
- In VMPR, some explicit descriptors also control EFSA's downstream legislative mapping, not only pass/fail validation. See [[vmpr-legislative-mapping]]. (VMPR mapping p3-6)

<!-- Source: docs/DOMAIN_SPECIFIC_RULES.md Implementation Matrix; docs/CONTEXT_SPECIFIC_RULES.md -->
## Common Mandatory Or Recommended Facets

| Context | Rule |
| --- | --- |
| VMPR standard animal products | `F01` and `F02` mandatory |
| VMPR processed or derivative products | explicit `F01` mandatory |
| VMPR wild or hunted samples | explicit `F21.A07RY` needed to trigger the `Wild` mapping |
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
- Before: a hunted or wild VMPR sample with no explicit `F21.A07RY`. After: the downstream mapping cannot create `Wild=1`, so the sample will stay on the ordinary game or parent-commodity route instead of the wild-game route. See [[vmpr-legislative-mapping]]. (VMPR mapping p5-6)
- Before: food additive sample with no `F33`. After: invalid for additives monitoring; the legislative category is mandatory. (Domain Specific Rules Additives)
- Before: acrylamide result on french fries (`A0BYV`) with no `F33`. After: `A0BYV#F33.A169H`. CHEMMON12 requires the acrylamide legislative class even though `A0BYV` may carry an implicit `F33`. (ChemMon 2026; CHEMMON12)

## Relevant Policy

- [[policy-contract]] `C07` and `C08` still govern domain overlays: even when a workflow requires explicit facets, the facet family and duplication logic must stay consistent with the chosen food type.
- [[policy-contract]] Decision Procedure step 5 is the main hook for this page. Apply these checks as a final domain overlay after ordinary FoodEx2 coding decisions have already been made.

## Relevant Business Rules

- `BR14` and `BR15`: context-specific validation paths such as ICT / DCF. See [[business-rules]].
- Domain overlays here should still be read alongside the core `BRxx` validator rules. Use [[business-rules]] as the canonical rule index when a domain case activates validation constraints.
