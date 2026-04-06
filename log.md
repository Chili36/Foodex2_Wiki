---
title: "Wiki Log"
last_updated: "2026-04-06"
---

# Log

## [2026-04-05] ingest | Initial FoodEx2 guidance compilation

- Created the first topic-oriented markdown pages under `raw/efsa-guidance/` from the EFSA FoodEx2 revision 2 guide, training materials, and chemical monitoring guidance.
- Seeded pages for overview, base-term selection, facet rules, implicit vs explicit facets, code-string format, process facets, and ingredient facets.
- Kept the source PDFs unchanged in `foodex2_docs/`.

## [2026-04-05] maintenance | Remove discontinued Smart Coding App references

- Deleted the standalone Smart Coding App page after confirming the app is discontinued.
- Re-checked the wiki layer to ensure no remaining `Smart Coding App` references remained.

## [2026-04-05] maintenance | Add repo context and wiki navigation

- Added `PROJECT_CONTEXT.md` to record what the project is building and why.
- Added `README.md` for repo-level orientation.
- Added `index.md` and `log.md` to support wiki navigation and chronological tracking.

## [2026-04-05] ingest | Add annual maintenance layer

- Added a cross-year maintenance timeline page.
- Added dedicated wiki pages for the annual maintenance reports covering 2015, 2016-2018, 2019, 2020, 2021, 2022, 2023 and 2024.
- Updated the index so the annual maintenance PDFs are now represented in the wiki layer instead of being left only in `foodex2_docs/`.

## [2026-04-05] ingest | Add Chemical Monitoring overlay

- Added a small page for the FoodEx2-specific rules embedded in the 2025 and 2026 Chemical Monitoring Reporting Guidance.
- Kept it separate from the core FoodEx2 guidance pages so reporting-workflow constraints do not get mixed with the base FoodEx2 model.

## [2026-04-05] ingest | Add validator rule layer

- Added dedicated wiki pages for structural validation, `BR01-BR31` overview, term-type facet constraints, process-rule conflicts, and domain-specific validation.
- Used the sibling `Foodex2 Code Validator` project as the source for the operational rule engine that had previously lived only in the coding prompt.
- Updated the index so the wiki now represents both EFSA guidance and the validator policy layer.

## [2026-04-05] ingest | Add packaging facet guidance

- Added a dedicated packaging page for `F18 Packaging-format` and `F19 Packaging-material`.
- Captured the distinction between packaging descriptors and `F28` process descriptors, including the fact that a `jar` does not by itself prove `pasteurisation`.
- Used the 2015 FoodEx2 guide and 2026 Chemical Monitoring examples as source material.

## [2026-04-05] service | Add wiki retrieval API

- Added a local FastAPI service under `wiki_api/` so external applications can call this repo for page reads and policy-pack retrieval.
- Kept the retrieval logic owned by the wiki repo instead of pushing wiki selection logic into downstream clients.
- Added tests for health, page listing, page reads, and a packaging-sensitive policy-pack case.

## [2026-04-05] service | Switch policy-pack retrieval to LLM librarian

- Replaced the deterministic page selector inside the API path with an internal Anthropic-powered wiki librarian.
- Kept the API surface stable for clients, but changed `/wiki/policy-pack` so the wiki repo now performs an actual LLM-guided read of the wiki before returning context.
- Added mocked tests for the LLM-owned policy-pack flow and included tool traces in the response metadata.

## [2026-04-06] maintenance | Add guiding principles to the wiki index

- Added a compact `Guiding Principles` section to `index.md` so the high-level FoodEx2 worldview is always available without consuming a separate page slot.
- Captured the key framing ideas that FoodEx2 is a scientific reporting language, is modeled top-down rather than bottom-up, prefers modular facets over term proliferation, and separates detailed input coding from downstream analytical aggregation.

## [2026-04-06] maintenance | Clarify derivative source vs added-ingredient logic

- Updated the facet and term-type pages to state the underlying origin-modeling rule explicitly: `F27` on a derivative answers what primary commodity the derivative was obtained from, while later-added characterising ingredients belong in `F04`.
- Kept the update generic and ontology-level, without adding a case-specific worked example.
