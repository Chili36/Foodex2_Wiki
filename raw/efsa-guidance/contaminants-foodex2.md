---
title: "FoodEx2 In Contaminants Monitoring"
select_when: >-
  The case is reported under contaminants or occurrence monitoring and needs
  substance-specific facets: arsenic/rice or chlorate processing, PAH packaging,
  acrylamide ingredients and legislative class, mycotoxin production method,
  cooking extent, fat content, target consumer, or sample preparation that
  differs from the pesticide interpretation.
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - Chemical monitoring reporting guidance  2025 data collection.pdf"
  - "Reportable Scallops list of FoodEx2 codes - MTX.xlsx"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[pesticides-foodex2]]"
  - "[[domoic-acid-scallops]]"
  - "[[domain-specific-validation]]"
  - "[[facet-coding-rules]]"
  - "[[implicit-vs-explicit-facets]]"
last_updated: "2026-09-30"
---

# FoodEx2 In Contaminants Monitoring

<!-- Source: ChemMon 2026 FoodEx2 mapping section; ChemMon 2026 Table 8 introduction; ChemMon 2026 CHEMMON12; ChemMon 2026 copper sample preparation examples -->
## Use Only When Contaminants Context Is Active

- This page is a conditional domain overlay. Use it when the request, reporting context, legal reference, parameter hierarchy, or candidate collection indicates contaminants monitoring.
- Typical activation signals include contaminants, occurrence, `OCC`, `chemAnalysis`, pyrrolizidine alkaloids, acrylamide, domoic acid, furans, bisphenols, phthalates, heavy metals, or a contaminants-domain candidate set.
- Do not apply pesticide MATRIX constraints to contaminants cases unless the request explicitly says the result is also being reported in the pesticide domain.

## Domain Boundary

- Contaminants coding still starts with ordinary FoodEx2 base-term selection from the MTX reporting hierarchy.
- Contaminants workflows can add substance-specific mandatory or recommended details. These requirements are updated in ChemMon guidance and should be treated as reporting overlays, not as universal FoodEx2 syntax.
- If a contaminant case names a botanical species or variety that is not available as a returned FoodEx2 candidate, use the best valid FoodEx2 candidate for the contaminants context and preserve the extra detail outside the code where the reporting workflow allows free text.

## High-Impact Rules

- Acrylamide monitoring is the clearest exception to normal implicit-facet cleanup: CHEMMON12 requires explicit `F33 Legislative-classes` for acrylamide results, even when the base term already has the relevant legislative class implicitly.
- Domoic acid in scallops has a source-provided matrix lookup. Use [[domoic-acid-scallops]] to select the exact `sampMatCode` and `sampMatText`, and include `origFishAreaCode` from FAREA wherever possible.
- Heat-treatment reporting for furans or acrylamide can require or recommend `F17 Cooking extent`.
- Bisphenol or phthalate analysis can require or recommend `F19 Packaging-material`.
- Fat-weight expression can require or recommend `F07 Fat-content`.
- Infant or baby-food reporting can require or recommend `F23 Target-consumer` when the base term does not already make the target consumer clear.

<!-- Source: ChemMon 2026 Table 8 p91, p93, p95-97 -->
## Substance-Specific Recommended Detail

These recommendations apply only to the named substance and matrix context. They supplement the ordinary base-term and facet rules; they are not universal requirements or automatic grounds for rejecting an otherwise valid code. Retain the mandatory acrylamide `F33` requirement separately.

| Context | Recommended FoodEx2 detail | Source |
| --- | --- | --- |
| Arsenic and derivatives: rice grains for human consumption | `F28` should distinguish unprocessed from processed rice; describe known treatment and whether the sample is dehydrated. Preserve the type of rice. | ChemMon 2026 Table 8 p95-96, CHEMON18 |
| Arsenic and derivatives: rice-based products or algae | Use `F04` to identify rice in rice-based products, and describe the algae in algae-based foods for special nutritional use. For seaweed, identify the presence of Hijiki when known. | ChemMon 2026 Table 8 p95-96 |
| Chlorates and perchlorates | Report `F28` with at least processed/unprocessed information, or the most appropriate known treatment, such as blanching or deep-freezing. | ChemMon 2026 Table 8 p97, CHEMON19 |
| Polycyclic aromatic hydrocarbons (PAH) | Report `F19` for the material of the container or wrapper holding the product as marketed. The laboratory sample container is a separate matter. See [[packaging-facets]]. | ChemMon 2026 Table 8 p93, CHEMON15 |
| Acrylamide: potato crisps; pre-cooked French fries/potato products for home cooking; breakfast cereals excluding muesli and porridge; dry substitute coffee; baby foods other than processed cereal-based foods | Provide ingredient detail in `F04` for these listed groups, in addition to the required `F33`. See [[ingredient-facets]] for ingredient-versus-source legality. | ChemMon 2026 Table 8 p91 |
| Mycotoxins | Report whether the product comes from traditional (non-organic) or organic farming using `F21`, when known. | ChemMon 2026 Table 8 p95, CHEMON17 |

- These recommendations do not justify inventing a treatment, ingredient, species or production method. Use available sample information and catalogue-confirmed descriptors; retain otherwise uncodeable detail in the appropriate text field.
- Preserve the correct food type and ordinary facet legality. Do not add a broad `processed` descriptor over a more specific implicit process, change a derivative into a raw commodity to attach `F28`, or use `F04` to replace the constitutive `F27` source of a derivative. For a source recommendation that cannot be expressed legally on the chosen term, retain the detail for reporting review rather than manufacture an invalid code.

## Pesticide Contrast

- Some contaminant and pesticide cases use different sample-preparation facets for the same matrix. For copper, contaminants examples include without peel, without shell, without stone, kernels without cob, roasted coffee beans, muscle with fat, and washed plant products.
- These contrasts are domain-specific. If the domain is contaminants, do not borrow pesticide preparation assumptions merely because the substance also appears in pesticide legislation.

## Worked Signals

- Acrylamide on french fries should include the explicit acrylamide legislative class facet, such as `A0BYV#F33.A169H`, when the acrylamide reporting rule is active.
- Domoic acid in scallops should use the species-and-part row from [[domoic-acid-scallops]] instead of a generic scallop code when the source sample identifies the analysed matrix.
- Copper in citrus fruit under contaminants should follow the contaminants preparation assumption, not the pesticide-residue with-peel assumption.
- Pyrrolizidine alkaloids in herbal infusion material should use the contaminants-context candidate set. Do not force the term into a pesticide Annex I MATRIX result unless pesticide reporting is explicit.

## Relevant Policy

- [[domain-specific-validation]] lists the contextual validation checks that turn these recommendations into blocking or warning behavior.
- [[pesticides-foodex2]] is separate because legal MATRIX mapping and sample-preparation assumptions can differ.
- [[implicit-vs-explicit-facets]] still applies unless a contaminants rule explicitly overrides it.
