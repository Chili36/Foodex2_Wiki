---
title: "Wiki Log"
last_updated: "2026-04-08"
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

## [2026-04-06] maintenance | Clarify derivative-base examples are illustrative

- Tightened the base-term selection wording so the list of nature-changing processes is explicitly illustrative rather than exhaustive.
- Added a note that the processed-base precedence rule should not be overridden just because a more specific raw commodity term exists.

## [2026-04-07] service | Add small compiled policy layer

- Added a small always-on policy contract to the API responses for `policy-pack` and `solve`.
- The contract includes a constitution, ordered decision procedure, binding rules, tie-break rules, and one explicit anti-pattern for raw-plus-`F28` reconstruction of standard derivative groups.
- Updated the solver so it treats this contract as the authoritative control layer and the wiki prose as supporting knowledge.

## [2026-04-07] maintenance | Move policy source into markdown

- Added `raw/efsa-guidance/policy-contract.md` as the source-of-truth policy page for the schema/control layer.
- Updated the API so it loads the policy contract from markdown frontmatter instead of defining it in service code.
- Linked the policy page from `index.md` so the schema layer is visible as part of the knowledge base.

## [2026-04-07] ingest | Add CHEMMON12 acrylamide F33 rule from EFSA clarification

- Added CHEMMON12 business rule detail to `domain-specific-validation.md`: paramCode trigger (`RF-00000410-ORG`), legal basis (Commission Regulation (EU) 2017/2158, Recommendation (EU) 2019/1888), and the implicit-override requirement.
- Added the implicit-facet exception to `implicit-vs-explicit-facets.md`: explicit `F33` is mandatory for acrylamide even when the base term already carries an implicit `F33`.
- Added a worked example to `chemical-monitoring-foodex2.md`: french fries `A0BYV#F33.A169H` with legislative class mapping.
- Source: EFSA official clarification on the ChemMon reporting channel, referencing CHEMMON12 and ChemMon 2026 guidance.

## [2026-04-08] maintenance | Add formal ingest workflow playbook

- Added `INGEST_WORKFLOW.md` as the concrete playbook for future document ingest.
- Captured the actual working method used in this repo: structure scan first, topic-map updates second, durable-rule extraction third, and gap-patching later.
- Linked the workflow from `README.md` and `index.md` so future maintenance work has an explicit reference process.

## [2026-04-08] maintenance | Strengthen inline cross-linking on core guidance pages

- Added body-level `[[...]]` cross-links to the main rule hubs so the model-facing API sees the same knowledge graph that humans infer from frontmatter and the viewer.
- Focused the pass on `base-term-selection.md`, `process-facets.md`, `ingredient-facets.md`, `implicit-vs-explicit-facets.md`, `term-type-facet-constraints.md`, `facet-coding-rules.md`, `process-validation-rules.md`, and `chemical-monitoring-foodex2.md`.
- Kept the links procedural rather than decorative: decision pages now point directly to adjacent rule pages for term type, origin-chain, process, validation, and ChemMon exceptions.

## [2026-04-08] service | Always include policy-contract.md in API page content

- Updated all three wiki API endpoints (context-pack, policy-pack, solve) to always include `policy-contract.md` in the `pages_used` list and `pages` content.
- The policy contract was already returned as structured data but its page content was not included unless the page selector happened to pick it. Now the constitution, binding rules, tie-break rules, and anti-patterns are always visible to the consuming model.

## [2026-04-08] maintenance | Add F27 narrowing rule for broad derivative groups

- Added a general rule to `implicit-vs-explicit-facets.md`: when a derivative base term carries a broad implicit F27, narrow it with an explicit F27 to the specific source commodity instead of abandoning the derivative and reconstructing from raw + F28.
- Added a corresponding row to the "When To Add An Explicit Facet" table for the broad-group derivative case.

## [2026-04-08] maintenance | Add related project links to README

- Added direct GitHub links in `README.md` to the sibling FoodEx2 validator project, the ChemMon wiki, and DMT.
- Made the repo-level orientation clearer for readers arriving without the surrounding project context.

## [2026-04-08] maintenance | Expand the policy contract with core coding ground rules

- Strengthened `raw/efsa-guidance/policy-contract.md` so the schema layer now carries more of the real FoodEx2 coding policy instead of only a thin constitutional shell.
- Added explicit policy rules for avoiding hierarchy terms, choosing the correct origin facet family by food type, and rejecting explicit facets that merely repeat implicit base-term properties.
- Bumped the policy version so API consumers can tell they are receiving the fuller contract.

## [2026-04-08] maintenance | Add operational coding rules to the policy contract

- Expanded `policy-contract.md` again with scope-note checking, processed-term priority, term-type-specific facet focus, descriptive facet guidance, process-ordinal constraints, single-cardinality limits, F27 refinement, F03/F01 restrictions, code syntax, SSD2 length limit, and monitoring-flag carry-through.
- Kept the rules in both forms: structured frontmatter for the machine-readable API contract and a readable "Operational Rules" section for humans consuming the page directly.
- Bumped the policy version from `v0.3` to `v0.4`.

## [2026-04-08] maintenance | Make the policy page body canonical and return it first

- Removed policy-specific frontmatter from `policy-contract.md` and moved the machine-readable rule sections into the visible markdown body so ordinary wiki consumers and API consumers now read the same policy text.
- Updated the policy loader to parse the body sections instead of relying on frontmatter-only rule data.
- Changed wiki API page ordering so `policy-contract.md` is always returned first in `pages_used` and `pages`.

## [2026-04-08] service | Tighten page-selector routing cues

- Expanded the wiki page selector prompt so it now treats candidate term types, monitoring flags, packaging clues, and raw-vs-derivative ambiguity as first-class routing signals rather than relying mostly on the user query text.
- Strengthened the relevant `index.md` summaries so domain and validation pages advertise VMPR/VETDRUG, raw-vs-derivative process conflicts, and ingredient-characterisation keywords more explicitly.

## [2026-04-09] ingest | Add cleaned validator business-rules source markdown

- Added `foodex2_docs/business_rules.md` as a cleaned source-layer markdown version of the validator's `BR01-BR31` rule set.
- Kept the content source-oriented and comprehensive, but stripped repeated severity boilerplate and formatting noise so future wiki ingests can work from a denser validator-policy artifact.

## [2026-04-09] maintenance | Add canonical business-rules wiki page and BR backlink workflow

- Added `raw/efsa-guidance/business-rules.md` as the canonical wiki target for `BR01`-`BR31`.
- Updated `index.md` so the validation layer now exposes that page directly.
- Updated `INGEST_WORKFLOW.md` to make business-rule backlinking mandatory for operational pages during ingest.
- Seeded `Relevant Business Rules` sections on the main validation pages so the pattern exists in the wiki itself, not just in process docs.

## [2026-04-09] maintenance | Backfill policy and business-rule traceability across all pages

- Added `Relevant Policy` sections across the full `raw/efsa-guidance/` set so every page now states which parts of `policy-contract.md` actually govern its use.
- Expanded `Relevant Business Rules` coverage across the full page set, including explicit "no single BRxx governs this page" language on conceptual and historical pages where that is the honest answer.
- Updated `INGEST_WORKFLOW.md` so future ingests must backfill both policy and business-rule relevance, not just validator-rule backlinks on operational pages.
