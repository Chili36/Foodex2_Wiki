---
title: "FoodEx2 In Pesticide Residue Monitoring"
select_when: >-
  The case is reported under pesticide residue monitoring, where the coded food
  must map to the legislative matrix catalogue and source-commodity facets can
  be decisive for processed foods, so the ordinary base-term choice carries
  extra pesticide-specific mapping consequences.
sources:
  - "EFSA Supporting Publications - 2026 -  - Chemical monitoring reporting guidance  2026 data collection.pdf"
  - "EFSA Supporting Publications - 2025 -  - FoodEx2 maintenance 2024.pdf"
  - "EFSA Supporting Publications - 2019 -  - FoodEx2 maintenance 2016-2018.pdf"
related:
  - "[[chemical-monitoring-foodex2]]"
  - "[[contaminants-foodex2]]"
  - "[[base-term-selection]]"
  - "[[implicit-vs-explicit-facets]]"
  - "[[maintenance-2016-2018]]"
  - "[[maintenance-2024]]"
last_updated: "2026-05-09"
---

# FoodEx2 In Pesticide Residue Monitoring

<!-- Source: ChemMon 2026 FoodEx2 mapping section; ChemMon 2026 Legal Limits database section; FoodEx2 maintenance 2016-2018 pesticide matrix-code updates; FoodEx2 maintenance 2024 pesticide matrix-code updates -->
## Use Only When Pesticide Context Is Active

- This page is a conditional domain overlay. Use it when the request, reporting context, legal reference, parameter hierarchy, or candidate collection indicates pesticide residue monitoring.
- Typical activation signals include pesticide residues, Regulation (EC) No 396/2005, `PEST`, `pestParam`, `MATRIX`, MRL, PRIMo, EUCP, or a pesticide-domain FoodEx2 candidate set.
- Do not apply pesticide MATRIX constraints to ordinary all-domain FoodEx2 coding, or to a contaminants case merely because the same substance could also be relevant to pesticides.

## Domain Boundary

- Pesticide monitoring still starts from the MTX reporting hierarchy and ordinary FoodEx2 base-term selection. The domain overlay affects whether the selected code maps to the pesticide legislative MATRIX catalogue.
- EFSA applies FoodEx2-to-MATRIX mapping downstream. Data providers report the correct FoodEx2 code; EFSA uses the mapping recorded in the FoodEx2/Catalogue Browser for pesticide legislative grouping.
- If the exact botanical variety or species is not a valid pesticide-domain matrix term, do not invent a FoodEx2 code. Use the most appropriate valid candidate returned for the domain and preserve additional botanical detail outside the code where the reporting workflow allows free text.
- The Legal Limits database for pesticide MRL evaluation is limited to raw, unprocessed samples. Processed or composite foods may still need FoodEx2 coding, but the legal-limit mapping is not the same as for raw commodities.

## Facet Consequences

- Source-commodity facets can be decisive for processed foods. Maintenance 2016-2018 removed broad pesticide matrix codes from many RPC derivatives and simple composites, so matches to raw primary commodities may depend on `F27 Source-commodities`.
- Do not fall back to a raw base term merely to satisfy a pesticide matrix idea. Keep the correct FoodEx2 food type, then add legally meaningful source facets when the chosen derivative or composite term requires them.
- Pesticide and contaminants contexts can require different preparation assumptions for the same matrix. For copper, pesticide-residue examples include with-peel, with-shell, with-stone, with-cob, green coffee beans, muscle after removal of trimmable fat, and unwashed plant products where the contaminants examples differ.

## Worked Signals

- A search term naming a regulated raw commodity in Annex I normally stays in the raw commodity branch and should use the pesticide-valid FoodEx2 candidate that maps to `MATRIX`.
- A processed cereal, dried pulse, juice, oil, or composite should not be recoded as a raw commodity just because pesticide legislation ultimately refers to raw primary commodities. Use the correct FoodEx2 base term and, where needed, `F27` to identify the source commodity.
- A plant name missing from the pesticide candidate set should be coded to the nearest valid pesticide-domain generic candidate rather than to an invented species-specific code.

## Relevant Policy

- [[base-term-selection]] remains the base-term authority. This page only adds the pesticide MATRIX constraint after the ordinary FoodEx2 type decision.
- [[contaminants-foodex2]] is a separate overlay. The two domains may produce different facet requirements for the same literal food text.
- [[implicit-vs-explicit-facets]] controls whether a source detail is already implicit or must be added explicitly.

